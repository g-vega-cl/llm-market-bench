import { useState } from 'react';
import { ChatInterface } from './ChatInterface';
import { ALLOWED_CHAT_EMAILS } from './chat-types';

interface ChatWidgetProps {
    user: { email: string } | null;
}

export function ChatWidget({ user }: ChatWidgetProps) {
    const [isOpen, setIsOpen] = useState(false);

    // Only render floating trigger for authorized accounts
    if (!user?.email || !ALLOWED_CHAT_EMAILS.includes(user.email)) {
        return null;
    }

    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end font-sans">
            {/* Chat Drawer / Window */}
            {isOpen && (
                <div className="mb-3 transition-all duration-300">
                    <ChatInterface
                        user={user}
                        isFullPage={false}
                        onClose={() => setIsOpen(false)}
                    />
                </div>
            )}

            {/* Floating Trigger Button */}
            <button
                type="button"
                aria-label="Chat"
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 rounded-full border border-cyan-500/40 bg-gradient-to-r from-zinc-950 via-slate-900 to-zinc-950 px-4 py-2.5 font-medium text-xs text-cyan-300 shadow-xl backdrop-blur-md transition-all duration-300 hover:scale-105 hover:border-cyan-400 hover:shadow-cyan-500/20 active:scale-95"
            >
                <span className="text-base">💬</span>
                <span>{isOpen ? 'Close Assistant' : 'Chat Assistant'}</span>
            </button>
        </div>
    );
}
