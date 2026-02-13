import { getSupabaseServerClient } from '~/lib/supabase'

export async function fetchPortfolios() {
  const supabase = getSupabaseServerClient()
  const { data, error } = await supabase
    .from('portfolios')
    .select('*')
    .order('total_equity', { ascending: false })

  if (error) throw error
  return data
}

export async function fetchPortfolioById(id: string) {
  const supabase = getSupabaseServerClient()
  const { data, error } = await supabase
    .from('portfolios')
    .select('*')
    .eq('id', id)
    .single()

  if (error) throw error
  return data
}

export async function fetchPositions(portfolioId: string) {
  const supabase = getSupabaseServerClient()

  // 1. Fetch current positions from the pnl view
  const { data: positions, error: posError } = await supabase
    .from('position_pnl')
    .select('*')
    .eq('portfolio_id', portfolioId)
    .order('ticker', { ascending: true })

  if (posError) throw posError
  if (!positions || positions.length === 0) return []

  const tickers = positions.map(p => p.ticker)

  // 2. Fetch latest decisions for these tickers
  // We don't join with trades here because many decisions lack trade_id or are for different portfolios.
  // Instead, we fetch the latest valid signals for these tickers.
  const { data: decisions, error: decError } = await supabase
    .from('decisions')
    .select('ticker, reasoning, signal, created_at, trade_id')
    .in('ticker', tickers)
    .order('created_at', { ascending: false })
    .limit(100)

  if (decError) throw decError

  // 3. Map reasoning to positions
  // Strategy: 
  // 1. If we have a trade_id match (not common but best), use it.
  // 2. Otherwise fall back to the most recent BUY/HOLD signal for that ticker.
  const reasoningMap = new Map<string, string>()

  // First pass: Ticker latest (since it's ordered by created_at desc)
  decisions?.forEach(d => {
    if (!reasoningMap.has(d.ticker)) {
      reasoningMap.set(d.ticker, d.reasoning)
    }
  })

  return positions.map(pos => ({
    ...pos,
    reasoning: reasoningMap.get(pos.ticker) || 'Reasoning not found in recent signals for this ticker.'
  }))
}

export async function fetchTrades(portfolioId: string) {
  const supabase = getSupabaseServerClient()

  // 1. Fetch trades
  const { data: trades, error: tradeError } = await supabase
    .from('trades')
    .select('*')
    .eq('portfolio_id', portfolioId)
    .order('executed_at', { ascending: false })
    .limit(50)

  if (tradeError) throw tradeError
  if (!trades || trades.length === 0) return []

  // 2. Fetch recent decisions for these tickers to fill in missing reasoning
  const tickers = Array.from(new Set(trades.map(t => t.ticker)))
  const { data: decisions, error: decError } = await supabase
    .from('decisions')
    .select('id, ticker, signal, reasoning, trade_id, created_at')
    .in('ticker', tickers)
    .order('created_at', { ascending: false })
    .limit(200)

  if (decError) throw decError

  // 3. Match decisions to trades
  return trades.map(trade => {
    // Try 1: Explicit decision_id on trade
    if (trade.decision_id) {
      const match = decisions?.find(d => d.id === trade.decision_id)
      if (match) return { ...trade, reasoning: match.reasoning }
    }

    // Try 2: Decision that points to this trade_id
    const tradePointerMatch = decisions?.find(d => d.trade_id === trade.id)
    if (tradePointerMatch) return { ...trade, reasoning: tradePointerMatch.reasoning }

    // Try 3: Latest decision for this ticker and signal that happened around the same time
    // We look for a decision within 24 hours of the trade
    const tradeTime = new Date(trade.executed_at).getTime()
    const proximityMatch = decisions?.find(d =>
      d.ticker === trade.ticker &&
      d.signal === trade.signal &&
      Math.abs(new Date(d.created_at).getTime() - tradeTime) < 24 * 60 * 60 * 1000
    )
    if (proximityMatch) return { ...trade, reasoning: proximityMatch.reasoning }

    // Try 4: Last resort - any latest decision for this ticker
    const fallbackMatch = decisions?.find(d => d.ticker === trade.ticker)

    return {
      ...trade,
      reasoning: fallbackMatch?.reasoning || 'Reasoning not linked to this specific trade record.'
    }
  })
}

export async function fetchPerformanceHistory(portfolioId: string) {
  const supabase = getSupabaseServerClient()
  const { data, error } = await supabase
    .from('portfolio_performance')
    .select('*')
    .eq('portfolio_id', portfolioId)
    .order('date', { ascending: true })

  if (error) throw error
  return data
}
