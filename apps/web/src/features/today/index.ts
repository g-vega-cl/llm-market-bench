/**
 * Today Feature
 *
 * Everything needed for the Today page — components, data fetching, and queries.
 *
 * @example
 * import { TodayPage } from '~/features/today'
 * import { fetchTodayData } from '~/features/today/api/fetch-today-data'
 */

export { TodayPage } from './pages/TodayPage'
export { fetchTodayData } from './api/fetch-today-data'
export { todayQueries } from './queries/options'
export { todayQueryKeys } from './queries/keys'

// Re-export key components for specialized layouts (optional)
export { MarketStatusHero } from './components/MarketStatusHero'
export { NewsletterFeed } from './components/NewsletterFeed'
export { TradeActivity } from './components/TradeActivity'
export { AgentInsights } from './components/AgentInsights'
export { FutureCatalysts } from './components/FutureCatalysts'
export { MarketUpdates } from './components/MarketUpdates'
