/**
 * Agent configuration and helpers for the Today feature.
 *
 * NOTE: This is internal to the Today feature slice.
 * Other features must not import from here.
 */

export const agentConfig: Record<string, { name: string; color: string; bgColor: string; emoji: string }> = {
  'gpt-5.4-nano': { name: 'OpenAI', color: 'text-emerald-500', bgColor: 'bg-emerald-500', emoji: '🟢' },
  'claude-haiku-4-5': { name: 'Claude', color: 'text-amber-600', bgColor: 'bg-amber-600', emoji: '🟠' },
  'gemini-3.1-flash-lite-preview': { name: 'Gemini', color: 'text-blue-500', bgColor: 'bg-blue-500', emoji: '🔵' },
  'deepseek-v4-flash': { name: 'DeepSeek', color: 'text-purple-500', bgColor: 'bg-purple-500', emoji: '🟣' },
  'contrarian_agent': { name: 'Contrarian', color: 'text-rose-500', bgColor: 'bg-rose-500', emoji: '🔴' },
}

export function getAgentInfo(ownerId: string | null | undefined) {
  if (!ownerId) return { name: 'Unknown', color: 'text-zinc-500', bgColor: 'bg-zinc-500', emoji: '⚪' }
  const normalized = ownerId.toLowerCase().replace(/_/g, '-').replace(/-/g, '-')
  for (const [key, config] of Object.entries(agentConfig)) {
    if (normalized.includes(key.replace(/-/g, '')) || key.includes(normalized.replace(/-/g, ''))) {
      return config
    }
  }
  return { name: ownerId, color: 'text-zinc-500', bgColor: 'bg-zinc-500', emoji: '⚪' }
}
