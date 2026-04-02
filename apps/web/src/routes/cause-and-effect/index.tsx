import { createFileRoute } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchCauseAndEffect } from './-queries'
import { CauseAndEffectList } from './components/-CauseAndEffectList'
import { useSuspenseQuery } from '@tanstack/react-query'
import { queries } from '~/lib/queries'
import * as React from 'react'
import { usePostHog } from '@posthog/react'

const getCauseAndEffect = createServerFn({ method: 'GET' }).handler(async () => {
  return fetchCauseAndEffect()
})

export const Route = createFileRoute('/cause-and-effect/')({
  loader: async () => await getCauseAndEffect(),
  component: CauseAndEffectPage,
})

function CauseAndEffectPage() {
  const posthog = usePostHog()
  const initialData = Route.useLoaderData()
  const getCauseAndEffectFn = useServerFn(getCauseAndEffect)

  const { data } = useSuspenseQuery({
    ...queries.causeAndEffect.list({ fetchFn: () => getCauseAndEffectFn() }),
    initialData,
  })

  React.useEffect(() => {
    posthog.capture('cause_and_effect_viewed')
  }, [])

  return (
    <div className="flex flex-col min-h-screen px-6 md:px-12 py-12">
      <div className="flex flex-col w-full">
        <header className="mb-12">
          <h1 className="text-4xl font-bold text-zinc-400 mb-4 tracking-tight">
            Cause & Effect Library
          </h1>
          <p className="text-zinc-400 text-lg leading-relaxed">
            A historical playbook of market reactions. Explore why the market moved
            following specific global events and use it as a frame for the future.
          </p>
        </header>

        <CauseAndEffectList entries={(data as any[]) || []} />
      </div>
    </div>
  )
}
