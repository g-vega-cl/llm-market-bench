import { CauseAndEffectCard } from './-CauseAndEffectCard'

export function CauseAndEffectList({ entries }: { entries: any[] }) {
  if (entries.length === 0) {
    return (
      <div className="text-zinc-500 py-12 text-center border border-dashed border-zinc-800 rounded-xl">
        No cause and effect entries found yet. The AI library is still growing.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-8">
      {entries.map((entry) => (
        <CauseAndEffectCard key={entry.id} entry={entry} />
      ))}
    </div>
  )
}
