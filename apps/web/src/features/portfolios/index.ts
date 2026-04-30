export { PortfoliosPage } from './pages/PortfoliosPage'
export { PortfolioDetailPage } from './pages/PortfolioDetailPage'
export { PortfolioComparisonChart } from './components/PortfolioComparisonChart'
export { PerformanceChart } from './components/PerformanceChart'
export { PositionsTable } from './components/PositionsTable'
export { TradesTable } from './components/TradesTable'
export { BenchmarkSelector, BENCHMARK_OPTIONS } from './components/BenchmarkSelector'
export {
  fetchPortfolios,
  fetchPortfolioById,
  fetchPositions,
  fetchTrades,
  fetchPerformanceHistory,
  fetchAllActivePortfolioPerformance,
  fetchBenchmarkHistory,
} from './api/fetch-portfolios'
export { portfolioQueries } from './queries/options'
export { portfolioQueryKeys } from './queries/keys'
export { getActiveOwnerIds, normalizeOwnerId } from './lib/config'
export type {
  BenchmarkDataPoint,
  PortfolioPerformanceItem,
} from './api/fetch-portfolios'
