import { Badge, Button, Card } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useEffect, useRef, useState } from 'react';
import { MarkdownContent } from '~/components/ui/MarkdownContent';
import { distillChatMemoryFn, saveChatMemoryFn, sendChatMessageFn } from './chat-server';
import {
    ALLOWED_CHAT_EMAILS,
    type ChatMemory,
    type ChatMessage,
    type DistillMemoryResult,
    SUGGESTED_RESEARCH_PROMPTS,
    type ToolTrace,
} from './chat-types';
import { PromoteMemoryModal } from './PromoteMemoryModal';

const STORAGE_KEY = 'benchify_chat_messages_v2';

const INITIAL_GREETING: ChatMessage = {
    role: 'assistant',
    content:
        '👋 Welcome to the **Benchify Investment Chat Gateway**!\n\nI have direct read access to your PostgreSQL database, past agent memory theses, daily newsletters, and trade execution logs. Ask me anything about stock tickers (e.g. *NVO*, *NVDA*), macroeconomic sentiment, or model performance.',
};

export interface ChatInterfaceProps {
    user: { email: string } | null;
    initialPrompt?: string;
    isFullPage?: boolean;
    onClose?: () => void;
}

function ToolTracesView({
    traces,
    isOpen,
    onToggle,
}: {
    traces: ToolTrace[];
    isOpen: boolean;
    onToggle: () => void;
}) {
    if (!traces.length) return null;
    return (
        <div className="mt-1.5 max-w-[90%] md:max-w-[85%] pl-1">
            <button
                type="button"
                onClick={onToggle}
                className="flex items-center gap-1.5 text-[11px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors bg-cyan-950/40 border border-cyan-800/40 rounded-lg px-2.5 py-1"
            >
                <span>⚡</span>
                <span>
                    {traces.length} tool {traces.length === 1 ? 'call' : 'calls'} executed
                </span>
                <span>{isOpen ? '▲' : '▼'}</span>
            </button>

            {isOpen && (
                <div className="mt-1.5 space-y-1 rounded-xl border border-zinc-800 bg-zinc-900/70 p-2.5 text-[11px] text-zinc-400">
                    {traces.map((trace) => (
                        <div
                            key={`${trace.tool_name}-${trace.summary}`}
                            className="flex items-start gap-2 border-b border-zinc-800/60 pb-1 last:border-b-0 last:pb-0"
                        >
                            <Badge variant="outline" size="sm" colorScheme="accent">
                                {trace.tool_name}
                            </Badge>
                            <span className="text-zinc-300 flex-1">{trace.summary}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function SuggestedQuestionsView({
    questions,
    onSelect,
}: {
    questions?: string[];
    onSelect: (q: string) => void;
}) {
    if (!questions || questions.length === 0) return null;

    return (
        <div className="mt-2.5 w-full max-w-[90%] md:max-w-[85%] pl-1 space-y-1.5">
            <p className="text-[11px] font-semibold text-zinc-400 flex items-center gap-1.5">
                <span className="text-cyan-400">💡</span>
                <span>Next best questions:</span>
            </p>
            <div className="flex flex-col gap-1.5">
                {questions.map((question) => (
                    <button
                        key={question}
                        type="button"
                        onClick={() => onSelect(question)}
                        className="text-left rounded-xl border border-cyan-900/50 bg-cyan-950/20 hover:bg-cyan-900/40 hover:border-cyan-500/60 p-2.5 text-xs text-zinc-200 hover:text-cyan-100 transition-all shadow-sm flex items-start gap-2 group"
                    >
                        <span className="text-cyan-400 shrink-0 font-mono text-[11px] group-hover:translate-x-0.5 transition-transform">
                            ↳
                        </span>
                        <span className="flex-1">{question}</span>
                    </button>
                ))}
            </div>
        </div>
    );
}

function MessageBubble({
    msg,
    isUser,
    isTraceOpen,
    onToggleTrace,
    showSuggestions,
    onSelectSuggestion,
    isDistilling,
    onPromoteMemory,
}: {
    msg: ChatMessage;
    isUser: boolean;
    isTraceOpen: boolean;
    onToggleTrace: () => void;
    showSuggestions: boolean;
    onSelectSuggestion: (q: string) => void;
    isDistilling?: boolean;
    onPromoteMemory?: () => void;
}) {
    const traces = msg.tool_traces || [];

    return (
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
            <div
                className={`rounded-2xl px-4 py-3 text-xs leading-relaxed max-w-[90%] md:max-w-[85%] ${
                    isUser
                        ? 'bg-cyan-600 text-white rounded-br-none shadow-md'
                        : 'bg-zinc-900/90 text-zinc-200 border border-zinc-800 rounded-bl-none shadow-sm'
                }`}
            >
                {isUser ? (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                ) : (
                    <MarkdownContent content={msg.content || ''} />
                )}
            </div>

            <ToolTracesView traces={traces} isOpen={isTraceOpen} onToggle={onToggleTrace} />

            {!isUser && onPromoteMemory && (
                <div className="mt-1.5 pl-1 flex items-center gap-2">
                    {msg.saved_memory_id ? (
                        <Badge
                            variant="outline"
                            size="sm"
                            colorScheme="success"
                            className="text-[11px] py-0.5"
                        >
                            ✓ Saved to My Theses
                        </Badge>
                    ) : (
                        <button
                            type="button"
                            onClick={onPromoteMemory}
                            disabled={isDistilling}
                            className="flex items-center gap-1.5 text-[11px] text-zinc-400 hover:text-cyan-300 transition-colors bg-zinc-900/80 hover:bg-zinc-800 border border-zinc-800 hover:border-cyan-800/60 rounded-lg px-2.5 py-1"
                        >
                            <span>{isDistilling ? '⏳' : '🧠'}</span>
                            <span>
                                {isDistilling ? 'Distilling thesis...' : 'Promote to Memory'}
                            </span>
                        </button>
                    )}
                </div>
            )}

            {showSuggestions && (
                <SuggestedQuestionsView
                    questions={msg.suggested_questions}
                    onSelect={onSelectSuggestion}
                />
            )}
        </div>
    );
}

function findPrecedingUserQuery(messages: ChatMessage[], currentIndex: number): string {
    for (let i = currentIndex - 1; i >= 0; i--) {
        const item = messages[i];
        if (item?.role === 'user' && item?.content) {
            return item.content;
        }
    }
    return 'General investment inquiry';
}

export function ChatInterface({
    user,
    initialPrompt,
    isFullPage = false,
    onClose,
}: ChatInterfaceProps) {
    const [messages, setMessages] = useState<ChatMessage[]>(() => {
        if (typeof window !== 'undefined') {
            try {
                const stored = localStorage.getItem(STORAGE_KEY);
                if (stored) {
                    const parsed = JSON.parse(stored);
                    if (Array.isArray(parsed) && parsed.length > 0) {
                        return parsed;
                    }
                }
            } catch {
                // Ignore parsing errors and use default greeting
            }
        }
        return [INITIAL_GREETING];
    });

    const [input, setInput] = useState(initialPrompt || '');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expandedTraces, setExpandedTraces] = useState<Record<number, boolean>>({});
    const [distillingIdx, setDistillingIdx] = useState<number | null>(null);
    const [modalState, setModalState] = useState<{
        isOpen: boolean;
        messageIndex: number;
        userQuery: string;
        assistantResponse: string;
        initialData: DistillMemoryResult;
    } | null>(null);

    const messagesEndRef = useRef<HTMLDivElement | null>(null);

    // Save to localStorage when messages change
    useEffect(() => {
        if (typeof window !== 'undefined' && messages.length > 0) {
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
            } catch {
                // Ignore localStorage errors
            }
        }
    }, [messages]);

    // Scroll to bottom
    // biome-ignore lint/correctness/useExhaustiveDependencies: scroll down on message addition
    useEffect(() => {
        if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages.length, isLoading]);

    // Handle initial prompt changes from query params
    useEffect(() => {
        if (initialPrompt?.trim()) {
            setInput(initialPrompt);
        }
    }, [initialPrompt]);

    const isAuthorized = Boolean(user?.email && ALLOWED_CHAT_EMAILS.includes(user.email));

    const handleClearHistory = () => {
        const resetMessages = [INITIAL_GREETING];
        setMessages(resetMessages);
        if (typeof window !== 'undefined') {
            localStorage.removeItem(STORAGE_KEY);
        }
    };

    const toggleTrace = (index: number) => {
        setExpandedTraces((prev) => ({ ...prev, [index]: !prev[index] }));
    };

    const handleStartPromote = async (msgIndex: number, visibleList: ChatMessage[]) => {
        const targetMsg = visibleList[msgIndex];
        if (!targetMsg?.content || distillingIdx !== null) return;

        const userQuery = findPrecedingUserQuery(visibleList, msgIndex);
        setDistillingIdx(msgIndex);
        setError(null);
        try {
            const distilled = await distillChatMemoryFn({
                data: {
                    userQuery,
                    assistantResponse: targetMsg.content,
                },
            });
            setModalState({
                isOpen: true,
                messageIndex: msgIndex,
                userQuery,
                assistantResponse: targetMsg.content,
                initialData: distilled,
            });
        } catch (err) {
            const errText = err instanceof Error ? err.message : 'Failed to distill thesis';
            setError(errText);
        } finally {
            setDistillingIdx(null);
        }
    };

    const handleModalSavedSuccess = (saved: ChatMemory, visibleList: ChatMessage[]) => {
        if (!modalState) return;
        const targetMsg = visibleList[modalState.messageIndex];
        if (!targetMsg) return;

        setMessages((prev) =>
            prev.map((m) => (m === targetMsg ? { ...m, saved_memory_id: saved.id } : m)),
        );
        setModalState(null);
    };

    const executeSend = async (messageText: string) => {
        const trimmed = messageText.trim();
        if (!trimmed || isLoading || !isAuthorized) return;

        const userMsg: ChatMessage = { role: 'user', content: trimmed };
        const updatedMessages = [...messages, userMsg];
        setMessages(updatedMessages);
        setInput('');
        setIsLoading(true);
        setError(null);

        try {
            const assistantMsg = await sendChatMessageFn({
                data: { messages: updatedMessages },
            });
            setMessages((prev) => [...prev, assistantMsg]);
        } catch (err) {
            const errText = err instanceof Error ? err.message : 'Failed to retrieve response';
            setError(errText);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        executeSend(input);
    };

    const handleChipClick = (prompt: string) => {
        setInput(prompt);
        executeSend(prompt);
    };

    if (!isAuthorized) {
        return (
            <Card className="w-full max-w-2xl mx-auto p-8 border-cyan-900/40 bg-zinc-950/80 backdrop-blur-xl shadow-2xl">
                <div className="flex items-center gap-3 mb-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-xl">
                        🔒
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h2 className="text-lg font-bold text-white tracking-tight">
                                Investment Chat Gateway
                            </h2>
                            <Badge variant="outline" colorScheme="accent">
                                Private Beta
                            </Badge>
                        </div>
                        <p className="text-xs text-zinc-400">
                            Gated conversational agent with real-time memory & database access
                        </p>
                    </div>
                </div>

                <div className="space-y-4 text-sm text-zinc-300">
                    <p className="leading-relaxed">
                        The Investment Chat Gateway is an interactive research interface allowing
                        you to interrogate market memories, review model theses, and ask questions
                        like{' '}
                        <code className="text-cyan-400 bg-zinc-900 px-1.5 py-0.5 rounded">
                            "Should I invest in NVO?"
                        </code>{' '}
                        grounded directly in live Supabase trading records.
                    </p>
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-2 text-xs text-zinc-400">
                        <p className="font-semibold text-zinc-200">
                            ✨ Available Capabilities when Authorized:
                        </p>
                        <ul className="list-disc list-inside space-y-1 pl-1">
                            <li>
                                Semantic search over agent memory cards and causal relationship
                                chains
                            </li>
                            <li>
                                Ticker deep-dives aggregating recent trades, PnL, and reasoning logs
                            </li>
                            <li>
                                Instant access to daily morning briefing newsletters and macro
                                sentiment
                            </li>
                            <li>Direct parameterized database queries against portfolio tables</li>
                        </ul>
                    </div>
                </div>

                <div className="mt-6 flex items-center justify-between pt-4 border-t border-zinc-800/80">
                    <span className="text-xs text-zinc-500">
                        {user ? `Signed in as ${user.email} (Access restricted)` : 'Not signed in'}
                    </span>
                    <Link to="/login">
                        <Button variant="solid" size="sm" colorScheme="accent">
                            Sign In to Access
                        </Button>
                    </Link>
                </div>
            </Card>
        );
    }

    const visibleMessages = messages.filter((msg) => msg.role !== 'tool' && msg.content);

    return (
        <div
            className={`flex flex-col rounded-2xl border border-zinc-800/80 bg-zinc-950/90 shadow-2xl backdrop-blur-xl transition-all ${
                isFullPage
                    ? 'w-full h-[calc(100vh-140px)] min-h-[580px]'
                    : 'h-[540px] w-96 max-w-[calc(100vw-2rem)]'
            }`}
        >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/60 px-4 py-3 rounded-t-2xl">
                <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 font-bold text-white text-sm shadow-md">
                        🤖
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-zinc-100 text-sm leading-none">
                                Benchify AI Gateway
                            </h3>
                            <Badge variant="soft" size="sm" colorScheme="accent">
                                Live DB Connected
                            </Badge>
                        </div>
                        <span className="text-[11px] text-zinc-400">
                            DeepSeek Flash · 4 Database Tools Enabled
                        </span>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        colorScheme="neutral"
                        onClick={handleClearHistory}
                        title="Clear conversation history"
                        className="text-xs text-zinc-400 hover:text-zinc-200"
                    >
                        Clear
                    </Button>
                    {onClose && (
                        <button
                            type="button"
                            aria-label="Close chat"
                            onClick={onClose}
                            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
                        >
                            ✕
                        </button>
                    )}
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-zinc-700">
                {visibleMessages.map((msg, idx) => {
                    const isUser = msg.role === 'user';
                    const isLatestAssistant = !isUser && idx === visibleMessages.length - 1;

                    return (
                        <MessageBubble
                            key={`${msg.role}-${msg.content?.slice(0, 30)}-${msg.tool_traces?.length ?? 0}`}
                            msg={msg}
                            isUser={isUser}
                            isTraceOpen={expandedTraces[idx] ?? false}
                            onToggleTrace={() => toggleTrace(idx)}
                            showSuggestions={Boolean(isLatestAssistant && !isLoading)}
                            onSelectSuggestion={handleChipClick}
                            isDistilling={distillingIdx === idx}
                            onPromoteMemory={
                                !isUser && msg !== INITIAL_GREETING
                                    ? () => handleStartPromote(idx, visibleMessages)
                                    : undefined
                            }
                        />
                    );
                })}

                {/* Loading indicator */}
                {isLoading && (
                    <div className="flex justify-start">
                        <div className="flex items-center gap-2 rounded-2xl rounded-bl-none border border-zinc-800 bg-zinc-900/90 px-4 py-3 text-xs text-cyan-400">
                            <span className="h-2 w-2 animate-ping rounded-full bg-cyan-400" />
                            <span>Benchify AI is querying database & analyzing memories...</span>
                        </div>
                    </div>
                )}

                {/* Error Banner */}
                {error && (
                    <div className="rounded-xl border border-red-500/30 bg-red-950/40 p-3 text-xs text-red-300">
                        ⚠️ {error}
                    </div>
                )}

                {/* Prompt Suggestions (if only greeting is present) */}
                {messages.length <= 1 && (
                    <div className="mt-4 space-y-2 pt-2 border-t border-zinc-800/60">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
                            Suggested Inquiries:
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {SUGGESTED_RESEARCH_PROMPTS.map((prompt) => (
                                <button
                                    key={prompt}
                                    type="button"
                                    onClick={() => handleChipClick(prompt)}
                                    className="text-left rounded-xl border border-zinc-800 bg-zinc-900/40 p-2.5 text-xs text-zinc-300 hover:border-cyan-500/50 hover:bg-cyan-950/20 hover:text-cyan-200 transition-all shadow-sm"
                                >
                                    💡 {prompt}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <form
                onSubmit={handleSubmit}
                className="border-t border-zinc-800 bg-zinc-900/80 p-3 rounded-b-2xl space-y-2"
            >
                <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                        Attach DB Context:
                    </span>
                    <button
                        type="button"
                        onClick={() =>
                            setInput(
                                (prev) =>
                                    `${prev ? `${prev} ` : ''}Please check the latest daily market briefing and market feeling.`,
                            )
                        }
                        className="px-2 py-0.5 rounded-md text-[11px] font-mono text-cyan-400 bg-zinc-900 border border-zinc-800 hover:border-cyan-500/50 hover:bg-cyan-950/30 transition-all"
                    >
                        📰 + Briefing
                    </button>
                    <button
                        type="button"
                        onClick={() =>
                            setInput(
                                (prev) =>
                                    `${prev ? `${prev} ` : ''}Please search our memories for recent market lessons and causal scenarios.`,
                            )
                        }
                        className="px-2 py-0.5 rounded-md text-[11px] font-mono text-cyan-400 bg-zinc-900 border border-zinc-800 hover:border-cyan-500/50 hover:bg-cyan-950/30 transition-all"
                    >
                        🧠 + Memories
                    </button>
                    <button
                        type="button"
                        onClick={() =>
                            setInput(
                                (prev) =>
                                    `${prev ? `${prev} ` : ''}Please query our recent trade decisions and portfolio leaderboard.`,
                            )
                        }
                        className="px-2 py-0.5 rounded-md text-[11px] font-mono text-cyan-400 bg-zinc-900 border border-zinc-800 hover:border-cyan-500/50 hover:bg-cyan-950/30 transition-all"
                    >
                        📊 + Portfolio Trades
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about a stock ticker, memory, or market feeling..."
                        disabled={isLoading}
                        className="flex-1 rounded-xl border border-zinc-700 bg-zinc-950 px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all disabled:opacity-50"
                    />
                    <Button
                        type="submit"
                        variant="solid"
                        size="sm"
                        colorScheme="accent"
                        disabled={isLoading || !input.trim()}
                        className="font-medium text-xs shadow-md shrink-0"
                    >
                        Send
                    </Button>
                </div>
            </form>

            {modalState && (
                <PromoteMemoryModal
                    isOpen={modalState.isOpen}
                    onClose={() => setModalState(null)}
                    userQuery={modalState.userQuery}
                    assistantResponse={modalState.assistantResponse}
                    initialData={modalState.initialData}
                    onSave={async (payload) => {
                        return await saveChatMemoryFn({ data: payload });
                    }}
                    onRedistill={async (instruction) => {
                        return await distillChatMemoryFn({
                            data: {
                                userQuery: modalState.userQuery,
                                assistantResponse: modalState.assistantResponse,
                                customInstruction: instruction,
                            },
                        });
                    }}
                    onSavedSuccess={(saved) => handleModalSavedSuccess(saved, visibleMessages)}
                />
            )}
        </div>
    );
}
