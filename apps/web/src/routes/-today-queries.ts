import { getSupabaseServerClient } from '~/lib/supabase'

export async function fetchTodayData() {
  const supabase = getSupabaseServerClient()

  // Calculate start of today in EST (America/New_York)
  // We use en-CA locale for YYYY-MM-DD format
  const now = new Date();
  const estDateStr = now.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });

  // We want to cover the entire day in EST.
  // In winter it's -05:00, in summer it's -04:00.
  // Using the offset in the string might be tricky if it changes,
  // but for most of the year -05:00 or -04:00 is fine.
  // Better yet, just use the date comparison if the DB supports it,
  // but with TIMESTAMPTZ it's better to be explicit.

  // A safer way to get the start of the day in UTC that corresponds to midnight EST:
  const startOfTodayEST = new Date(new Date(estDateStr).toLocaleString('en-US', { timeZone: 'UTC' }));
  // Wait, that's not quite right.

  // Let's just use a simple approach:
  const startOfDay = `${estDateStr}T00:00:00`
  // And let the database interpret it or just use the date string if we can cast.

  // 1. Newsletters
  const { data: newsletters } = await supabase
    .from('newsletter_snapshots')
    .select('*')
    .gte('date', startOfDay)
    .order('date', { ascending: false })

  // 2. Trades
  const { data: trades } = await supabase
    .from('trades')
    .select('*, portfolios(owner_id)')
    .gte('executed_at', startOfDay)
    .order('executed_at', { ascending: false })

  // 3. Decisions (including rejections)
  const { data: decisions } = await supabase
    .from('decisions')
    .select('*')
    .gte('created_at', startOfDay)
    .order('created_at', { ascending: false })

  // 4. Reasoning Logs
  const { data: logs } = await supabase
    .from('llm_reasoning_logs')
    .select('*')
    .gte('created_at', startOfDay)
    .order('created_at', { ascending: false })

  // 5. Memories (Consensus / Lessons)
  const { data: memories } = await supabase
    .from('memories')
    .select('*')
    .gte('created_at', startOfDay)
    .order('created_at', { ascending: false })

  // 6. Price Updates (from market_data_cache fetched today)
  const { data: priceUpdates } = await supabase
    .from('market_data_cache')
    .select('*')
    .gte('fetched_at', startOfDay)
    .order('fetched_at', { ascending: false })

  // 7. Future Events
  // We look for high-importance catalysts and exclude past events.
  // Importance threshold: >= 8
  const { data: futureEvents } = await supabase
    .from('memories')
    .select('*')
    .eq('status', 'ACTIVE')
    .gte('importance_score', 8)
    .or(`target_date.is.null,target_date.gte.${estDateStr}`)
    .or('metadata->is_future_catalyst.eq.true,target_date.not.is.null')
    .order('created_at', { ascending: false })

  return {
    newsletters: newsletters || [],
    trades: trades || [],
    decisions: decisions || [],
    logs: logs || [],
    memories: memories || [],
    priceUpdates: priceUpdates || [],
    futureEvents: futureEvents || []
  }
}
