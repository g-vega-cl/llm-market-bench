import { createFileRoute } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { fetchMemories } from './-queries'
import { MemoriesList } from './components/-MemoriesList'

const getMemories = createServerFn({ method: 'GET' }).handler(async () => {
  return fetchMemories()
})

export const Route = createFileRoute('/memories/')({
  loader: async () => await getMemories(),
  component: MemoriesPage,
})

function MemoriesPage() {
  const memories = Route.useLoaderData()

  return (
    <div className="stack gap-fluid-2xl">
      <header className="stack gap-fluid-xs">
        <h1 className="text-fluid-4xl font-black text-zinc-900 dark:text-white tracking-tighter">
          AI Memories & Insights
        </h1>
        <p className="text-zinc-500 text-fluid-lg max-w-2xl">
          Explore the collective intelligence of our LLMs. From global market news to trade post-mortems, 
          this is where the AI stores its long-term market perspective.
        </p>
      </header>
      
      <MemoriesList memories={memories || []} />
    </div>
  )
}
