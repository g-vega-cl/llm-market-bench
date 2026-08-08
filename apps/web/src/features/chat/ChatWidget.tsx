import { useEffect, useRef, useState } from 'react';
import { sendChatMessageFn } from './chat-server';
import { ALLOWED_CHAT_EMAILS, type ChatMessage } from './chat-types';

interface ChatWidgetProps {
    user: { email: string } | null;
}

export function ChatWidget({ user }: ChatWidgetProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            role: 'assistant',
            content:
                'Hello! I am your Benchify AI assistant powered by DeepSeek Flash. How can I help you analyze market data or strategies today?',
        },
    ]);

    const messagesEndRef = useRef<HTMLDivElement | null>(null);

    // biome-ignore lint/correctness/useExhaustiveDependencies: scroll to bottom when messages array changes or drawer opens
    useEffect(() => {
        if (isOpen && typeof messagesEndRef.current?.scrollIntoView === 'function') {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages.length, isOpen]);

    // Account Gating Check
    if (!user?.email || !ALLOWED_CHAT_EMAILS.includes(user.email)) {
        return null;
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const trimmed = input.trim();
        if (!trimmed || isLoading) return;

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
            const errText = err instanceof Error ? err.message : 'Failed to send message';
            setError(errText);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end font-sans">
            {/* Chat Drawer / Window */}
            {isOpen && (
                <div className="mb-3 flex h-[520px] w-96 max-w-[calc(100vw-2rem)] flex-col rounded-2xl border border-slate-700/60 bg-slate-900/95 shadow-2xl backdrop-blur-xl transition-all duration-300">
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/80 px-4 py-3 rounded-t-2xl">
                        <div className="flex items-center gap-2.5">
                            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 font-bold text-white text-xs shadow-md">
                                🤖
                            </div>
                            <div>
                                <h3 className="font-semibold text-slate-100 text-sm leading-none">
                                    Benchify AI
                                </h3>
                                <span className="text-[11px] text-cyan-400 font-medium">
                                    DeepSeek Flash MVP
                                </span>
                            </div>
                        </div>
                        <div className="flex items-center gap-1">
                            <button
                                type="button"
                                aria-label="Close chat"
                                onClick={() => setIsOpen(false)}
                                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
                            >
                                ✕
                            </button>
                        </div>
                    </div>

                    {/* Messages Container */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-slate-700">
                        {messages
                            .filter((msg) => msg.role !== 'tool' && msg.content)
                            .map((msg, idx) => (
                                <div
                                    // biome-ignore lint/suspicious/noArrayIndexKey: simple sequential chat log
                                    key={`${msg.role}-${idx}`}
                                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div
                                        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
                                            msg.role === 'user'
                                                ? 'bg-blue-600 text-white rounded-br-none shadow-md'
                                                : 'bg-slate-800/90 text-slate-200 border border-slate-700/50 rounded-bl-none shadow-sm'
                                        }`}
                                    >
                                        {msg.content}
                                    </div>
                                </div>
                            ))}

                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-none border border-slate-700/50 bg-slate-800/90 px-4 py-3 text-xs text-slate-400">
                                    <span className="h-1.5 w-1.5 animate-ping rounded-full bg-cyan-400" />
                                    <span>DeepSeek is thinking...</span>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="rounded-xl border border-red-500/30 bg-red-950/40 p-3 text-xs text-red-300">
                                ⚠️ {error}
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Form */}
                    <form
                        onSubmit={handleSubmit}
                        className="border-t border-slate-800 bg-slate-900/90 p-3 rounded-b-2xl"
                    >
                        <div className="flex items-center gap-2">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Type a message..."
                                disabled={isLoading}
                                className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all disabled:opacity-50"
                            />
                            <button
                                type="submit"
                                aria-label="Send"
                                disabled={isLoading || !input.trim()}
                                className="flex h-8 items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-3.5 font-medium text-xs text-white shadow-md transition-all hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                Send
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Floating Trigger Button */}
            <button
                type="button"
                aria-label="Chat"
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 rounded-full border border-cyan-500/40 bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 px-4 py-2.5 font-medium text-xs text-cyan-300 shadow-xl backdrop-blur-md transition-all duration-300 hover:scale-105 hover:border-cyan-400 hover:shadow-cyan-500/20 active:scale-95"
            >
                <span className="text-base">💬</span>
                <span>{isOpen ? 'Close Assistant' : 'Chat Assistant'}</span>
            </button>
        </div>
    );
}
