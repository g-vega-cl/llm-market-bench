import { getSupabaseServerClient } from '~/lib/supabase'
import type {
  NewsletterSnapshot,
  MarketDataCache,
  Decision,
  Trade,
  LLMReasoningLog,
  Memory,
  MarketFeeling
} from '@llm-market-bench/database'

export async function fetchTodayData() {
  const supabase = getSupabaseServerClient()

  const now = new Date();
  const estDateStr = now.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });

  const startOfDay = `${estDateStr}T00:00:00`

  const { data: newsletters } = await supabase
    .from('newsletter_snapshots')
    .select('*')
    .gte('date', startOfDay)
    .order('date', { ascending: false })

  const { data: trades } = await supabase
    .from('trades')
    .select('*, portfolios(owner_id)')
    .gte('executed_at', startOfDay)
    .order('executed_at', { ascending: false })

  const { data: decisions } = await supabase
    .from('decisions')
    .select('*')
    .gte('created_at', startOfDay)
    .order('created_at', { ascending: false })

  const { data: logs } = await supabase
    .from('llm_reasoning_logs')
    .select('*')
    .gte('created_at', startOfDay)
    .order('created_at', { ascending: false })

  const { data: memories } = await supabase
    .from('memories')
    .select('*')
    .gte('created_at', startOfDay)
    .order('created_at', { ascending: false })

  const { data: priceUpdates } = await supabase
    .from('market_data_cache')
    .select('*')
    .gte('fetched_at', startOfDay)
    .order('fetched_at', { ascending: false })

  const { data: futureEvents } = await supabase
    .from('memories')
    .select('*')
    .eq('status', 'ACTIVE')
    .gte('importance_score', 8)
    .eq('metadata->is_future_catalyst', true)
    .or(`target_date.is.null,target_date.gte.${estDateStr}`)
    .order('created_at', { ascending: false })

  const { data: marketFeeling } = await supabase
    .from('market_feeling')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(1)

  return {
    newsletters: (newsletters || []) as NewsletterSnapshot[],
    trades: (trades || []) as (Trade & { portfolios: { owner_id: string } })[],
    decisions: (decisions || []) as Decision[],
    logs: (logs || []) as LLMReasoningLog[],
    memories: (memories || []) as Memory[],
    priceUpdates: (priceUpdates || []) as MarketDataCache[],
    futureEvents: (futureEvents || []) as Memory[],
    marketFeeling: (marketFeeling?.[0] || null) as MarketFeeling | null
  }
}
