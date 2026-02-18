import { createFileRoute } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { fetchReasoningLogs } from './-queries'
import * as React from 'react'

const getReasoningLogs = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchReasoningLogs()
})

export const Route = createFileRoute('/reasoning/')({
    loader: async () => await getReasoningLogs(),
    component: ReasoningPage,
})

interface ReasoningTrace {
    id: string
    task_type: string
    model_provider: string
    model_name: string
    prompt: any[]
    response: any
    metadata: any
    created_at: string
}

function ReasoningPage() {
    const logs = Route.useLoaderData() as ReasoningTrace[]
    const [activeTab, setActiveTab] = React.useState<string>('ALL')
    const [selectedLogId, setSelectedLogId] = React.useState<string | null>(null)

    const categories = ['ALL', ...new Set(logs?.map((l) => l.task_type) || [])]

    const filteredLogs = activeTab === 'ALL'
        ? logs
        : logs?.filter((l) => l.task_type === activeTab)

    const selectedLog = logs?.find((l) => l.id === selectedLogId)

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 p-6 md:p-12 animate-slow-fade">
            <header className="mb-12">
                <h1 className="text-5xl font-extrabold mb-4 tracking-tighter bg-gradient-to-r from-blue-500 to-teal-400 bg-clip-text text-transparent">
                    LLM Research Audit Trail
                </h1>
                <p className="text-gray-500 dark:text-gray-400 text-xl max-w-3xl leading-relaxed font-light">
                    The ultimate source of truth for agent cognition. Every tool call, every prompt, and every internal "thought" trace is captured here for deep research and auditing.
                </p>
            </header>

            {/* Tabs */}
            <div className="flex flex-wrap gap-2 mb-8 p-1.5 bg-gray-100 dark:bg-gray-900/50 rounded-2xl w-fit border border-gray-200 dark:border-gray-800 backdrop-blur-xl">
                {categories.map((cat) => (
                    <button
                        key={cat}
                        onClick={() => setActiveTab(cat)}
                        className={`px-6 py-2.5 rounded-xl text-xs font-bold uppercase tracking-widest transition-all duration-300 ${activeTab === cat
                            ? 'bg-white dark:bg-blue-600 shadow-xl text-blue-600 dark:text-white border-b-2 border-blue-500 dark:border-blue-400'
                            : 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'
                            }`}
                    >
                        {cat}
                    </button>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Logs List */}
                <div className="lg:col-span-4 space-y-4 max-h-[75vh] overflow-y-auto pr-4 scrollbar-thin scrollbar-thumb-blue-500/20 scrollbar-track-transparent">
                    {filteredLogs?.map((log) => (
                        <div
                            key={log.id}
                            onClick={() => setSelectedLogId(log.id)}
                            className={`p-5 rounded-3xl border transition-all cursor-pointer group hover:shadow-2xl hover:-translate-y-1 ${selectedLogId === log.id
                                ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-900/20 shadow-2xl ring-1 ring-blue-500/50'
                                : 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/40 hover:border-blue-300 dark:hover:border-blue-700 shadow-sm'
                                }`}
                        >
                            <div className="flex justify-between items-start mb-3">
                                <span className="px-3 py-1 rounded-full text-[10px] uppercase font-black tracking-widest bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                                    {log.task_type}
                                </span>
                                <span className="text-[10px] text-gray-400 font-mono italic">
                                    {new Date(log.created_at).toLocaleTimeString()}
                                </span>
                            </div>
                            <h3 className="font-bold text-gray-800 dark:text-gray-100 text-lg leading-tight group-hover:text-blue-500 transition-colors">
                                {log.metadata?.ticker || 'Global Analysis'}
                            </h3>
                            <div className="flex items-center gap-2 mt-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                                <p className="text-[11px] font-medium text-gray-500 dark:text-gray-500 tracking-wide uppercase">
                                    {log.model_provider} • {log.model_name}
                                </p>
                            </div>
                        </div>
                    ))}
                    {(!filteredLogs || filteredLogs.length === 0) && (
                        <div className="text-center py-12 p-8 border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-3xl text-gray-400 italic">
                            No logs found for this category.
                        </div>
                    )}
                </div>

                {/* Trace Viewer */}
                <div className="lg:col-span-8 bg-white dark:bg-gray-900/60 rounded-[2.5rem] border border-gray-200 dark:border-gray-800 p-10 shadow-3xl backdrop-blur-3xl relative overflow-hidden h-[75vh] flex flex-col group/viewer">
                    {/* Decorative Background Glow */}
                    <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />

                    {!selectedLog ? (
                        <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
                            <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center animate-pulse">
                                <div className="w-8 h-8 rounded bg-gray-200 dark:bg-gray-700" />
                            </div>
                            <p className="italic font-light text-lg">Select a reasoning trace to inspect the thinking process.</p>
                        </div>
                    ) : (
                        <>
                            <div className="flex justify-between items-start mb-8 pb-8 border-b border-gray-100 dark:border-gray-800/50">
                                <div>
                                    <div className="flex items-center gap-3 mb-2">
                                        <h2 className="text-3xl font-black text-gray-900 dark:text-white tracking-tight">
                                            {selectedLog.metadata?.ticker || selectedLog.task_type}
                                        </h2>
                                        <span className="px-3 py-1 rounded-lg bg-blue-500/10 text-blue-500 text-[10px] uppercase font-black tracking-widest border border-blue-500/20">
                                            Audit Mode
                                        </span>
                                    </div>
                                    <p className="text-xs text-gray-400 font-mono tracking-tighter bg-gray-100 dark:bg-gray-800/50 px-2 py-1 rounded-md w-fit">
                                        UUID: {selectedLog.id} • {new Date(selectedLog.created_at).toLocaleString()}
                                    </p>
                                </div>
                            </div>

                            <div className="flex-1 overflow-y-auto space-y-10 pr-6 scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent">
                                {/* Conversation Trace */}
                                <HumanFriendlyPrompt prompt={selectedLog.prompt} />

                                {/* Final Response */}
                                <HumanFriendlyResponse response={selectedLog.response} />
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

export function HumanFriendlyPrompt({ prompt }: { prompt: any[] }) {
    const roles = ['ALL', ...new Set(prompt?.map(m => m.role) || [])]
    const [activeRole, setActiveRole] = React.useState('ALL')

    const filteredMessages = activeRole === 'ALL'
        ? prompt
        : prompt?.filter(m => m.role === activeRole)

    const shouldShowTabs = (prompt?.length || 0) > 3

    return (
        <section>
            <div className="flex items-center justify-between gap-4 mb-6">
                <div className="flex items-center gap-4 flex-1">
                    <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">Cognitive Flow</h4>
                    <div className="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-800 to-transparent" />
                </div>
                {shouldShowTabs && (
                    <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-inner">
                        {roles.map(role => (
                            <button
                                key={role}
                                onClick={() => setActiveRole(role)}
                                className={`px-4 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all duration-200 ${activeRole === role
                                    ? 'bg-white dark:bg-blue-600 text-blue-600 dark:text-white shadow-sm ring-1 ring-black/5'
                                    : 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'
                                    }`}
                            >
                                {role}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            <div className="space-y-6">
                {filteredMessages?.map((msg, idx) => {
                    const isSystem = msg.role === 'system'
                    const isAssistant = msg.role === 'assistant' || msg.role === 'model'
                    const isTool = msg.role === 'tool' || (msg.parts && msg.parts.some((p: any) => p.function_response))

                    return (
                        <div key={idx} className={`p-6 rounded-[1.5rem] border transition-all hover:shadow-lg ${isSystem ? 'bg-gray-50/50 dark:bg-gray-800/20 border-gray-200 dark:border-gray-700/50' :
                            isAssistant ? 'bg-blue-50/30 dark:bg-blue-600/5 border-blue-100 dark:border-blue-500/20 shadow-sm' :
                                isTool ? 'bg-emerald-50/30 dark:bg-emerald-600/5 border-emerald-100 dark:border-emerald-500/20' :
                                    'bg-white dark:bg-gray-900/40 border-gray-200 dark:border-gray-800 shadow-sm'
                            }`}>
                            <div className="flex items-center gap-2 mb-3">
                                <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md ${isSystem ? 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400' :
                                    isAssistant ? 'bg-blue-500 text-white' :
                                        isTool ? 'bg-emerald-500 text-white' :
                                            'bg-gray-800 text-white'
                                    }`}>
                                    {msg.role}
                                </span>
                            </div>
                            <div className="text-xs font-mono leading-relaxed text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words selection:bg-blue-500/30">
                                <FormattedContent content={msg.content || msg.parts || msg} />
                            </div>
                        </div>
                    )
                })}
            </div>
        </section>
    )
}

function FormattedContent({ content }: { content: any }) {
    if (typeof content === 'string') {
        try {
            // Try to parse as JSON if it looks like JSON
            if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
                const parsed = JSON.parse(content)
                return <pre className="font-mono text-[11px] leading-relaxed">{JSON.stringify(parsed, null, 2)}</pre>
            }
        } catch (e) {
            // Not JSON, just return string
        }
        return <>{content}</>
    }

    if (Array.isArray(content)) {
        return (
            <div className="space-y-4">
                {content.map((part, i) => (
                    <div key={i} className="border-l-2 border-gray-200 dark:border-gray-700 pl-4 py-1">
                        {part.text && <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{part.text}</p>}
                        {part.thought && (
                            <div className="bg-amber-50/50 dark:bg-amber-900/10 p-3 rounded-xl border border-amber-100 dark:border-amber-900/20">
                                <span className="text-[9px] font-black text-amber-600 dark:text-amber-500 uppercase tracking-widest block mb-1">Internal Thought</span>
                                <p className="text-amber-800 dark:text-amber-200 italic font-light">{part.thought}</p>
                            </div>
                        )}
                        {part.function_call && (
                            <div className="bg-blue-50/50 dark:bg-blue-900/10 p-3 rounded-xl border border-blue-100 dark:border-blue-900/20">
                                <span className="text-[9px] font-black text-blue-600 dark:text-blue-500 uppercase tracking-widest block mb-1">Tool Call: {part.function_call.name}</span>
                                <pre className="text-[10px] font-mono text-blue-800 dark:text-blue-300">{JSON.stringify(part.function_call.args, null, 2)}</pre>
                            </div>
                        )}
                        {part.function_response && (
                            <div className="bg-emerald-50/50 dark:bg-emerald-900/10 p-3 rounded-xl border border-emerald-100 dark:border-emerald-900/20">
                                <span className="text-[9px] font-black text-emerald-600 dark:text-emerald-500 uppercase tracking-widest block mb-1">Tool Response: {part.function_response.name}</span>
                                <pre className="text-[10px] font-mono text-emerald-800 dark:text-emerald-300">{JSON.stringify(part.function_response.response, null, 2)}</pre>
                            </div>
                        )}
                        {!part.text && !part.thought && !part.function_call && !part.function_response && (
                            <pre className="text-[10px] font-mono">{JSON.stringify(part, null, 2)}</pre>
                        )}
                    </div>
                ))}
            </div>
        )
    }

    return <pre className="font-mono text-[11px] leading-relaxed">{JSON.stringify(content, null, 2)}</pre>
}

export function HumanFriendlyResponse({ response }: { response: any }) {
    if (!response || typeof response !== 'object') {
        return (
            <section>
                <div className="flex items-center gap-4 mb-6">
                    <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">Output Schema</h4>
                    <div className="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-800 to-transparent" />
                </div>
                <div className="relative group/raw">
                    <pre className="p-8 bg-[#0D0D10] text-[#7DD3FC] rounded-[2.5rem] text-[11px] font-mono overflow-x-auto border border-white/5 shadow-2xl leading-relaxed">
                        {JSON.stringify(response, null, 2)}
                    </pre>
                    <button
                        onClick={() => navigator.clipboard.writeText(JSON.stringify(response, null, 2))}
                        className="absolute top-4 right-4 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-[9px] font-bold uppercase tracking-wider opacity-0 group-hover/raw:opacity-100 transition-opacity"
                    >
                        Copy JSON
                    </button>
                </div>
            </section>
        )
    }

    const keys = Object.keys(response)
    const [activeTab, setActiveTab] = React.useState(keys[0] || 'RAW')

    const displayedKeys = [...keys, 'RAW']

    return (
        <section>
            <div className="flex items-center justify-between gap-4 mb-6">
                <div className="flex items-center gap-4 flex-1">
                    <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">Output Schema</h4>
                    <div className="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-800 to-transparent" />
                </div>
                <div className="flex flex-wrap gap-1 p-1 bg-gray-100 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-inner">
                    {displayedKeys.map(key => (
                        <button
                            key={key}
                            onClick={() => setActiveTab(key)}
                            className={`px-4 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all duration-200 ${activeTab === key
                                ? 'bg-white dark:bg-blue-600 text-blue-600 dark:text-white shadow-sm ring-1 ring-black/5'
                                : 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'
                                }`}
                        >
                            {key.replace(/_/g, ' ')}
                        </button>
                    ))}
                </div>
            </div>

            <div className="mt-4">
                {activeTab === 'RAW' ? (
                    <div className="relative group/raw">
                        <pre className="p-8 bg-[#0D0D10] text-[#7DD3FC] rounded-[2.5rem] text-[11px] font-mono overflow-x-auto border border-white/5 shadow-2xl leading-relaxed thought-step-glow">
                            {JSON.stringify(response, null, 2)}
                        </pre>
                        <button
                            onClick={() => navigator.clipboard.writeText(JSON.stringify(response, null, 2))}
                            className="absolute top-6 right-6 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-[10px] font-bold uppercase tracking-widest opacity-0 group-hover/raw:opacity-100 transition-all active:scale-95"
                        >
                            Copy JSON
                        </button>
                    </div>
                ) : (
                    <div className="animate-slow-fade">
                        <ResponseDataView value={response[activeTab]} label={activeTab} />
                    </div>
                )}
            </div>
        </section>
    )
}

function ResponseDataView({ value, label }: { value: any, label: string }) {
    if (Array.isArray(value)) {
        return (
            <div className="grid grid-cols-1 gap-4">
                {value.map((item, i) => (
                    <DataCard key={i} item={item} />
                ))}
                {value.length === 0 && <p className="text-gray-500 italic text-xs">Empty list.</p>}
            </div>
        )
    }

    if (typeof value === 'object' && value !== null) {
        return <DataCard item={value} />
    }

    // Primitive value
    const isLongText = typeof value === 'string' && value.length > 100

    return (
        <div className={`p-6 rounded-[1.5rem] border bg-white dark:bg-gray-900/40 border-gray-200 dark:border-gray-800 shadow-sm ${isLongText ? 'col-span-full' : ''}`}>
            <h5 className="text-[9px] font-black uppercase tracking-widest text-gray-400 mb-2">{label.replace(/_/g, ' ')}</h5>
            <div className={`text-sm ${isLongText ? 'leading-relaxed text-gray-700 dark:text-gray-300' : 'font-bold text-gray-900 dark:text-white'}`}>
                {String(value)}
            </div>
        </div>
    )
}

function DataCard({ item }: { item: any }) {
    if (typeof item !== 'object' || item === null) {
        return <div className="p-4 border border-gray-200 dark:border-gray-800 rounded-2xl bg-gray-50/50 dark:bg-gray-900/50 font-mono text-xs">{String(item)}</div>
    }

    const entries = Object.entries(item)
    // Identify "summary" or "reasoning" fields to give them more space
    const longTextFields = entries.filter(([k, v]) => typeof v === 'string' && (v.length > 60 || k.includes('reasoning') || k.includes('summary')))
    const shortFields = entries.filter(([k, v]) => !longTextFields.find(([lk]) => lk === k))

    return (
        <div className="p-8 rounded-[2.5rem] border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/40 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all duration-300 group/card">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {shortFields.map(([k, v]) => (
                    <div key={k} className="space-y-1">
                        <h6 className="text-[9px] font-black uppercase tracking-widest text-gray-400 group-hover/card:text-blue-500/60 transition-colors">{k.replace(/_/g, ' ')}</h6>
                        <div className="text-[13px] font-bold text-gray-900 dark:text-gray-100 break-words">
                            {typeof v === 'boolean' ? (
                                <span className={`px-2 py-0.5 rounded-md text-[10px] ${v ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600' : 'bg-rose-100 dark:bg-rose-900/30 text-rose-600'}`}>
                                    {v ? 'YES' : 'NO'}
                                </span>
                            ) : String(v)}
                        </div>
                    </div>
                ))}
            </div>
            {longTextFields.length > 0 && (
                <div className="mt-8 space-y-8 pt-8 border-t border-gray-100 dark:border-gray-800/50">
                    {longTextFields.map(([k, v]) => (
                        <div key={k} className="space-y-3">
                            <h6 className="text-[9px] font-black uppercase tracking-widest text-gray-400 group-hover/card:text-blue-500/60 transition-colors">{k.replace(/_/g, ' ')}</h6>
                            <div className="text-[13px] leading-relaxed text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-light bg-gray-50/50 dark:bg-gray-950/30 p-4 rounded-2xl border border-gray-100 dark:border-gray-800/50">
                                {String(v)}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
