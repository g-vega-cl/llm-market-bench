/**
 * Reasoning Feature
 *
 * LLM Research Audit Trail — every tool call, prompt, and thought trace.
 *
 * @example
 * import { ReasoningPage } from '~/features/reasoning'
 * import { fetchReasoningLogs } from '~/features/reasoning/api/fetch-reasoning-logs'
 */

export { ReasoningPage } from './pages/ReasoningPage'

export { fetchReasoningLogs, fetchAllReasoningLogs } from './api/fetch-reasoning-logs'
export { reasoningQueries } from './queries/options'
export { reasoningQueryKeys } from './queries/keys'

// Re-export viewer components for specialized use cases
export { HumanFriendlyPrompt } from './components/HumanFriendlyPrompt'
export { HumanFriendlyResponse } from './components/HumanFriendlyResponse'
export { FormattedContent } from './components/FormattedContent'
export { DataCard } from './components/DataCard'
