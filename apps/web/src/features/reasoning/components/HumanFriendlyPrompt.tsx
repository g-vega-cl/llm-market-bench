import * as React from 'react';
import { FormattedContent } from './FormattedContent';

export function HumanFriendlyPrompt({ prompt }: { prompt: any[] }) {
    const roles = ['ALL', ...new Set(prompt?.map((m) => m.role) || [])];
    const [activeRole, setActiveRole] = React.useState('ALL');

    const filteredMessages =
        activeRole === 'ALL' ? prompt : prompt?.filter((m) => m.role === activeRole);

    const shouldShowTabs = (prompt?.length || 0) > 3;

    return (
        <section>
            <div className="flex items-center justify-between gap-2 md:gap-4 mb-4 md:mb-6">
                <div className="flex items-center gap-2 md:gap-4 flex-1 min-w-0">
                    <h4 className="text-[9px] md:text-[10px] font-black text-gray-400 uppercase tracking-[0.15em] md:tracking-[0.2em] whitespace-nowrap">
                        Cognitive Flow
                    </h4>
                    <div className="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-800 to-transparent min-w-[20px]" />
                </div>
                {shouldShowTabs && (
                    <div className="flex gap-0.5 md:gap-1 p-0.5 md:p-1 bg-gray-100 dark:bg-gray-900 rounded-lg md:rounded-xl border border-gray-200 dark:border-gray-800 shadow-inner overflow-x-auto">
                        {roles.map((role) => (
                            <button
                                key={role}
                                onClick={() => setActiveRole(role)}
                                className={`px-2 md:px-4 py-1 md:py-1.5 rounded-md md:rounded-lg text-[8px] md:text-[9px] font-black uppercase tracking-widest transition-all duration-200 whitespace-nowrap min-h-[32px] md:min-h-[unset] ${
                                    activeRole === role
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

            <div className="space-y-3 md:space-y-6">
                {filteredMessages?.map((msg, idx) => {
                    const isSystem = msg.role === 'system';
                    const isAssistant = msg.role === 'assistant' || msg.role === 'model';
                    const isTool =
                        msg.role === 'tool' ||
                        (msg.parts && msg.parts.some((p: any) => p.function_response));

                    return (
                        <div
                            key={idx}
                            className={`p-4 md:p-6 rounded-xl md:rounded-[1.5rem] border transition-all hover:shadow-lg ${
                                isSystem
                                    ? 'bg-gray-50/50 dark:bg-gray-800/20 border-gray-200 dark:border-gray-700/50'
                                    : isAssistant
                                      ? 'bg-blue-50/30 dark:bg-blue-600/5 border-blue-100 dark:border-blue-500/20 shadow-sm'
                                      : isTool
                                        ? 'bg-emerald-50/30 dark:bg-emerald-600/5 border-emerald-100 dark:border-emerald-500/20'
                                        : 'bg-white dark:bg-gray-900/40 border-gray-200 dark:border-gray-800 shadow-sm'
                            }`}
                        >
                            <div className="flex items-center gap-1.5 md:gap-2 mb-2 md:mb-3">
                                <span
                                    className={`text-[8px] md:text-[9px] font-black uppercase tracking-widest px-1.5 md:px-2 py-0.5 rounded-md ${
                                        isSystem
                                            ? 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                                            : isAssistant
                                              ? 'bg-blue-500 text-white'
                                              : isTool
                                                ? 'bg-emerald-500 text-white'
                                                : 'bg-gray-800 text-white'
                                    }`}
                                >
                                    {msg.role}
                                </span>
                            </div>
                            <div className="text-[11px] md:text-xs font-mono leading-relaxed text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words selection:bg-blue-500/30 overflow-x-hidden">
                                <FormattedContent content={msg.content || msg.parts || msg} />
                            </div>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}
