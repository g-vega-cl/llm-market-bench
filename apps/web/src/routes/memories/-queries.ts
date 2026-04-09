import { getSupabaseBrowserClient } from '~/lib/supabase-client'
import type { Memory } from '@llm-market-bench/database'

const PAGE_SIZE = 50

export interface PaginatedMemories {
  data: Memory[]
  hasMore: boolean
  nextCursor: string | null
}

export async function fetchMemories(cursor?: string, pageSize: number = PAGE_SIZE): Promise<PaginatedMemories> {
  const supabase = getSupabaseBrowserClient()
  
  let query = supabase
    .from('memories')
    .select('*, parent_id, status, relationship_type')
    .order('created_at', { ascending: false })
    .limit(pageSize + 1)

  if (cursor) {
    query = query.lt('created_at', cursor)
  }

  const { data, error } = await query

  if (error) throw error

  const hasMore = data.length > pageSize
  const paginatedData = hasMore ? data.slice(0, pageSize) : data

  const nextCursor = hasMore && paginatedData.length > 0
    ? paginatedData[paginatedData.length - 1].created_at
    : null

  return {
    data: paginatedData,
    hasMore,
    nextCursor
  }
}

export async function fetchAllMemories() {
  const supabase = getSupabaseBrowserClient()
  const { data, error } = await supabase
    .from('memories')
    .select('*, parent_id, status, relationship_type')
    .order('created_at', { ascending: false })

  if (error) throw error
  return data
}
