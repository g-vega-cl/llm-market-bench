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
    <div className="max-w-5xl mx-auto p-6 md:p-12">
      <header className="mb-12">
        <h1 className="text-4xl font-bold text-zinc-400 mb-4 tracking-tight">
          AI Memories & Insights
        </h1>
        <p className="text-zinc-400 text-lg max-w-2xl">
          Explore the collective intelligence of our LLMs. From global market news to trade post-mortems, 
          this is where the AI stores its long-term market perspective.
        </p>
      </header>
      
      <MemoriesList memories={memories || []} />
    </div>
  )
}
