import { createFileRoute, redirect } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { getSupabaseServerClient } from '../utils/supabase'

const exchangeCodeFn = createServerFn({ method: 'GET' })
  .inputValidator((d: { code: string }) => d)
  .handler(async ({ data }) => {
    const supabase = getSupabaseServerClient()
    const { error } = await supabase.auth.exchangeCodeForSession(data.code)
    if (error) {
      console.error('Error exchanging code for session:', error.message)
    }
  })

export const Route = createFileRoute('/auth/callback')({
  validateSearch: (search: Record<string, unknown>) => {
    return {
      code: search.code as string | undefined,
    }
  },
  loaderDeps: ({ search: { code } }) => ({ code }),
  loader: async ({ deps: { code } }) => {
    if (code) {
      await exchangeCodeFn({ data: { code } })
    }
    throw redirect({ to: '/' })
  },
})
