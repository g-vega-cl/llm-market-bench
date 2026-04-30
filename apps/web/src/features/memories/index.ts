/**
 * Memories Feature
 *
 * Everything for AI memories: list view, detail cards, flow visualization, and event chains.
 *
 * @example
 * import { MemoriesPage, EventChainPage } from '~/features/memories'
 * import { fetchMemories } from '~/features/memories/api/fetch-memories'
 */

export { MemoriesPage } from './pages/MemoriesPage'
export { EventChainPage } from './pages/EventChainPage'

export { fetchMemories, fetchAllMemories } from './api/fetch-memories'
export { memoriesQueries, eventChainQueries } from './queries/options'
export { memoriesQueryKeys, eventChainQueryKeys } from './queries/keys'

// Re-export key components for use in other features if needed
export { MemoriesList } from './components/MemoriesList'
export { MemoryCard } from './components/MemoryCard'
export { MemoryFlow } from './components/MemoryFlow'
