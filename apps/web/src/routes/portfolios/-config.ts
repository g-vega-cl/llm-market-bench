/**
 * Portfolio configuration utilities
 */

import { normalizeOwnerId } from './-queries'

// Load models.json - using a dynamic path that works in both dev and build
// TanStack Start requires JSON imports to be handled carefully
const MODELS_JSON_PATH = '../../../../packages/config/models.json'

let cachedActiveOwnerIds: string[] | null = null

/**
 * Returns the list of active owner IDs from the models.json config.
 * These are the owner_ids that should be considered "active" portfolios.
 * Portfolios with owner_ids not in this list are considered deprecated/retired.
 */
export function getActiveOwnerIds(): string[] {
  if (cachedActiveOwnerIds) {
    return cachedActiveOwnerIds
  }

  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const modelsConfig = require(MODELS_JSON_PATH) as Record<string, string>
    const values = Object.values(modelsConfig)
    
    // Normalize all owner IDs for consistent comparison
    cachedActiveOwnerIds = values.map(id => normalizeOwnerId(id))
    return cachedActiveOwnerIds
  } catch (error) {
    console.error('Failed to load models.json:', error)
    // Fallback to empty array - this will mark all portfolios as deprecated
    return []
  }
}
