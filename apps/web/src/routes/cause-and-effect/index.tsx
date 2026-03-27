import { createFileRoute } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchCauseAndEffect } from './-queries'
import { CauseAndEffectList } from './components/-CauseAndEffectList'
import { useSuspenseQuery } from '@tanstack/react-query'
import { queries } from '~/lib/queries'

const getCauseAndEffect = createServerFn({ method: 'GET' }).handler(async () => {
  return fetchCauseAndEffect()
})

export const Route = createFileRoute('/cause-and-effect/')({
  loader: async () => await getCauseAndEffect(),
  component: CauseAndEffectPage,
})

function CauseAndEffectPage() {
  const initialData = Route.useLoaderData()
  const getCauseAndEffectFn = useServerFn(getCauseAndEffect)

  const { data } = useSuspenseQuery({
    ...queries.causeAndEffect.list(() => getCauseAndEffectFn()),
    initialData,
  })

  return (
    <div className="max-w-5xl mx-auto p-6 md:p-12">
      <header className="mb-12">
        <h1 className="text-4xl font-bold text-zinc-400 mb-4 tracking-tight">
          Cause & Effect Library
        </h1>
        <p className="text-zinc-400 text-lg max-w-2xl">
          A historical playbook of market reactions. Explore why the market moved
          following specific global events and use it as a frame for the future.
        </p>
      </header>

      <CauseAndEffectList entries={(data as any[]) || []} />
    </div>
  )
}
