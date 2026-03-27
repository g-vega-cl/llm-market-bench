import { getSupabaseBrowserClient } from '~/lib/supabase-client'

const PAGE_SIZE = 50

export interface Memory {
  id: string
  content: string
  created_at: string
  metadata: any
  status?: 'ACTIVE' | 'RESOLVED' | 'SUPERSEDED'
  parent_id?: string
  relationship_type?: 'REVERSAL' | 'UPDATE' | 'RESOLUTION' | 'GENERAL'
}

export interface PaginatedMemories {
  data: Memory[]
  hasMore: boolean
  nextCursor: string | null
}

/**
 * Fetch memories with cursor-based pagination
 * @param cursor - The created_at timestamp of the last item from previous page
 * @param pageSize - Number of items per page (default: 50)
 */
export async function fetchMemories(cursor?: string, pageSize: number = PAGE_SIZE): Promise<PaginatedMemories> {
  const supabase = getSupabaseBrowserClient()
  
  let query = supabase
    .from('memories')
    .select('*, parent_id, status, relationship_type')
    .order('created_at', { ascending: false })
    .limit(pageSize + 1) // Fetch one extra to check if there's more

  if (cursor) {
    query = query.lt('created_at', cursor)
  }

  const { data, error } = await query

  if (error) throw error

  // Check if we have more data
  const hasMore = data.length > pageSize
  const paginatedData = hasMore ? data.slice(0, pageSize) : data

  // Get the cursor for the next page
  const nextCursor = hasMore && paginatedData.length > 0
    ? paginatedData[paginatedData.length - 1].created_at
    : null

  return {
    data: paginatedData,
    hasMore,
    nextCursor
  }
}

/**
 * Fetch all memories (legacy - use only for small datasets)
 * @deprecated Use fetchMemories with pagination instead
 */
export async function fetchAllMemories() {
  const supabase = getSupabaseBrowserClient()
  const { data, error } = await supabase
    .from('memories')
    .select('*, parent_id, status, relationship_type')
    .order('created_at', { ascending: false })

  if (error) throw error
  return data
}
