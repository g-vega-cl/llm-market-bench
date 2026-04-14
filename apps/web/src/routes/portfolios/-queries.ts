import { getSupabaseServerClient } from '~/lib/supabase'
import { getActiveOwnerIds } from './-config'
import type { 
  Portfolio, 
  Trade, 
  PositionPnl, 
  Decision,
  PortfolioPerformance,
  PositionWithReasoning,
  TradeWithReasoning
} from '@llm-market-bench/database'

export async function fetchPortfolios(): Promise<(Portfolio & { is_active: boolean })[]> {
  const supabase = getSupabaseServerClient()
  const { data, error } = await supabase
    .from('portfolios')
    .select('*')
    .order('total_equity', { ascending: false })

  if (error) throw error

  const activeIds = new Set(getActiveOwnerIds())
  return data.map((p) => ({
    ...p,
    is_active: activeIds.has(normalizeOwnerId(p.owner_id)),
  }))
}

export function normalizeOwnerId(ownerId: string | null): string {
  if (!ownerId) return ''
  return ownerId
    .toLowerCase()
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export async function fetchPortfolioById(id: string): Promise<Portfolio> {
  const supabase = getSupabaseServerClient()
  const { data, error } = await supabase
    .from('portfolios')
    .select('*')
    .eq('id', id)
    .single()

  if (error) throw error
  return data
}

export async function fetchPositions(portfolioId: string): Promise<PositionWithReasoning[]> {
  const supabase = getSupabaseServerClient()

  const { data: positions, error: posError } = await supabase
    .from('position_pnl')
    .select('*')
    .eq('portfolio_id', portfolioId)
    .order('ticker', { ascending: true })

  if (posError) throw posError
  if (!positions || positions.length === 0) return []

  const tickers = positions.map(p => p.ticker)

  const { data: decisions, error: decError } = await supabase
    .from('decisions')
    .select('ticker, reasoning, signal, created_at, trade_id')
    .in('ticker', tickers)
    .order('created_at', { ascending: false })
    .limit(100)

  if (decError) throw decError

  const reasoningMap = new Map<string, string>()

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

export async function fetchTrades(portfolioId: string): Promise<TradeWithReasoning[]> {
  const supabase = getSupabaseServerClient()

  const { data: trades, error: tradeError } = await supabase
    .from('trades')
    .select('*')
    .eq('portfolio_id', portfolioId)
    .order('executed_at', { ascending: false })
    .limit(50)

  if (tradeError) throw tradeError
  if (!trades || trades.length === 0) return []

  const tickers = Array.from(new Set(trades.map(t => t.ticker)))
  const { data: decisions, error: decError } = await supabase
    .from('decisions')
    .select('id, ticker, signal, reasoning, trade_id, created_at')
    .in('ticker', tickers)
    .order('created_at', { ascending: false })
    .limit(200)

  if (decError) throw decError

  return trades.map(trade => {
    if (trade.decision_id) {
      const match = decisions?.find(d => d.id === trade.decision_id)
      if (match) return { ...trade, reasoning: match.reasoning }
    }

    const tradePointerMatch = decisions?.find(d => d.trade_id === trade.id)
    if (tradePointerMatch) return { ...trade, reasoning: tradePointerMatch.reasoning }

    const tradeTime = new Date(trade.executed_at).getTime()
    const proximityMatch = decisions?.find(d =>
      d.ticker === trade.ticker &&
      d.signal === trade.signal &&
      Math.abs(new Date(d.created_at).getTime() - tradeTime) < 24 * 60 * 60 * 1000
    )
    if (proximityMatch) return { ...trade, reasoning: proximityMatch.reasoning }

    const fallbackMatch = decisions?.find(d => d.ticker === trade.ticker)

    return {
      ...trade,
      reasoning: fallbackMatch?.reasoning || 'Reasoning not linked to this specific trade record.'
    }
  })
}

export async function fetchPerformanceHistory(portfolioId: string): Promise<PortfolioPerformance[]> {
  const supabase = getSupabaseServerClient()
  const { data, error } = await supabase
    .from('portfolio_performance')
    .select('*')
    .eq('portfolio_id', portfolioId)
    .order('date', { ascending: true })

  if (error) throw error
  return data
}

export interface BenchmarkDataPoint {
  date: string
  price: number
}

export async function fetchBenchmarkHistory(
  tickers: string[],
  startDate: string,
  endDate: string
): Promise<Record<string, BenchmarkDataPoint[]>> {
  if (tickers.length === 0) return {}

  const supabase = getSupabaseServerClient()
  const { data, error } = await supabase
    .from('price_history')
    .select('ticker, price, fetched_at')
    .in('ticker', tickers)
    .gte('fetched_at', startDate)
    .lte('fetched_at', endDate)
    .order('fetched_at', { ascending: true })

  if (error) throw error

  const result: Record<string, BenchmarkDataPoint[]> = {}
  for (const ticker of tickers) {
    result[ticker] = []
  }

  data?.forEach(row => {
    if (result[row.ticker]) {
      result[row.ticker].push({
        date: row.fetched_at.split('T')[0],
        price: Number(row.price)
      })
    }
  })

  return result
}
