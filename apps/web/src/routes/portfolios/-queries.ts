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
  const { data, error } = await supabase
    .from('position_pnl')
    .select('*')
    .eq('portfolio_id', portfolioId)
    .order('ticker', { ascending: true })

  if (error) throw error
  return data
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
