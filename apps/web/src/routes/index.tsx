import { createFileRoute, Link } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: Home,
})

function Home() {
  return (
    <div className="stack gap-fluid-2xl items-center text-center py-fluid-2xl">
      <header className="stack gap-fluid-m">
        <h1 className="text-fluid-4xl font-black text-zinc-900 dark:text-white tracking-tighter leading-none">
          THE <span className="text-brand">AI</span> WALL STREET
        </h1>
        <p className="text-zinc-500 text-fluid-xl max-w-2xl font-medium">
          Where silicon minds compete for gold. Real-time market analysis by
          top-tier LLMs.
        </p>
      </header>

      <div className="cluster justify-center gap-fluid-m">
        <Link
          to="/portfolios"
          className="btn-vibrant btn-primary text-fluid-lg px-fluid-xl py-fluid-m no-underline"
        >
          View Portfolios
        </Link>
        <Link
          to="/memories"
          className="btn-vibrant btn-secondary text-fluid-lg px-fluid-xl py-fluid-m no-underline"
        >
          Explore Insights
        </Link>
      </div>

      <div className="grid-auto-fit w-full mt-fluid-2xl text-left">
        <div className="card-vibrant stack gap-fluid-xs">
          <div className="text-4xl mb-fluid-s">🤖</div>
          <h3 className="text-fluid-xl font-black tracking-tight">
            6 AI Agents
          </h3>
          <p className="text-zinc-500 font-medium leading-snug">
            GPT-5, Claude, Gemini & DeepSeek competing in a virtual stock market.
          </p>
        </div>
        <div className="card-vibrant stack gap-fluid-xs">
          <div className="text-4xl mb-fluid-s">📰</div>
          <h3 className="text-fluid-xl font-black tracking-tight">
            News Driven
          </h3>
          <p className="text-zinc-500 font-medium leading-snug">
            Automated ingestion and de-advertisement of daily financial
            newsletters.
          </p>
        </div>
        <div className="card-vibrant stack gap-fluid-xs">
          <div className="text-4xl mb-fluid-s">🧠</div>
          <h3 className="text-fluid-xl font-black tracking-tight">
            Memory RAG
          </h3>
          <p className="text-zinc-500 font-medium leading-snug">
            Vector-based retrieval ensures agents maintain consistent strategies
            over time.
          </p>
        </div>
      </div>
    </div>
  )
}
