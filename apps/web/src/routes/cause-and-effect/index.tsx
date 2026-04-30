import { createFileRoute } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchCauseAndEffect } from '~/features/cause-and-effect/api/fetch-cause-and-effect'
import { CauseAndEffectPage } from '~/features/cause-and-effect/pages/CauseAndEffectPage'

const getCauseAndEffect = createServerFn({ method: 'GET' }).handler(async () => {
  return fetchCauseAndEffect()
})

export const Route = createFileRoute('/cause-and-effect/')({
  loader: async () => await getCauseAndEffect(),
  component: RouteComponent,
})

function RouteComponent() {
  const initialData = Route.useLoaderData()
  const getCauseAndEffectFn = useServerFn(getCauseAndEffect)

  return (
    <CauseAndEffectPage
      initialData={initialData}
      fetchFn={() => getCauseAndEffectFn()}
    />
  )
}
