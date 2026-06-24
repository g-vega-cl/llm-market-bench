/**
 * Today Feature
 *
 * Everything needed for the Today page — components, data fetching, and queries.
 *
 * @example
 * import { TodayPage } from '~/features/today'
 * import { fetchTodayData } from '~/features/today/api/fetch-today-data'
 */

export { fetchTodayData } from './api/fetch-today-data';
export { AgentInsights } from './components/AgentInsights';
export { FutureCatalysts } from './components/FutureCatalysts';
// Re-export key components for specialized layouts (optional)
export { MarketStatusHero } from './components/MarketStatusHero';
export { MarketUpdates } from './components/MarketUpdates';
export { NewsletterFeed } from './components/NewsletterFeed';
export { TodayStatusBar } from './components/TodayStatusBar';
export { TradeActivity } from './components/TradeActivity';
export { TodayPage } from './pages/TodayPage';
export { todayQueryKeys } from './queries/keys';
export { todayQueries } from './queries/options';
