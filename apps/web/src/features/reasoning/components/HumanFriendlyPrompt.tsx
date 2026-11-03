import { Badge, Button } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { FormattedContent } from './FormattedContent';

interface PromptMessage {
    role: string;
    content?: string;
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    parts?: any[]; // Parts can be complex and model-specific
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    [key: string]: any;
}

export function HumanFriendlyPrompt({
    prompt: rawPrompt,
}: {
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    prompt: PromptMessage[] | Record<string, any>;
}) {
    const prompt = Array.isArray(rawPrompt) ? (rawPrompt as PromptMessage[]) : [];
    const roles = ['ALL', ...new Set(prompt?.map((m) => m.role) || [])];
    const [activeRole, setActiveRole] = React.useState('ALL');

    const filteredMessages =
        activeRole === 'ALL' ? prompt : prompt?.filter((m) => m.role === activeRole);

    const shouldShowTabs = (prompt?.length || 0) > 3;

    return (
        <section className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                    <h4 className="text-sm font-bold text-gray-400 uppercase tracking-wider whitespace-nowrap m-0">
                        Cognitive Flow
                    </h4>
                    <div className="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-800 to-transparent min-w-[20px]" />
                </div>
                {shouldShowTabs && (
                    <div className="flex gap-1 p-1 bg-zinc-100 dark:bg-zinc-900 rounded-none border border-zinc-200 dark:border-zinc-800 shadow-inner overflow-x-auto">
                        {roles.map((role) => (
                            <Button
                                key={role}
                                size="sm"
                                variant={activeRole === role ? 'solid' : 'ghost'}
                                colorScheme={activeRole === role ? 'accent' : 'neutral'}
                                onClick={() => setActiveRole(role)}
                                className="rounded-none text-sm font-bold"
                            >
                                {role}
                            </Button>
                        ))}
                    </div>
                )}
            </div>

            <div className="flex flex-col gap-4">
                {filteredMessages?.map((msg, idx) => {
                    const isSystem = msg.role === 'system';
                    const isAssistant = msg.role === 'assistant' || msg.role === 'model';
                    const isTool =
                        msg.role === 'tool' ||
                        msg.parts?.some(
                            (p: { function_response?: unknown; [key: string]: unknown }) =>
                                p.function_response,
                        );

                    return (
                        <div
                            key={idx}
                            className={`p-4 rounded-none border transition-all flex flex-col gap-2 ${
                                isSystem
                                    ? 'bg-gray-50/50 dark:bg-gray-800/20 border-gray-200 dark:border-gray-700/50'
                                    : isAssistant
                                      ? 'bg-blue-50/30 dark:bg-blue-600/5 border-blue-100 dark:border-blue-500/20 shadow-sm'
                                      : isTool
                                        ? 'bg-emerald-50/30 dark:bg-emerald-600/5 border-emerald-100 dark:border-emerald-500/20'
                                        : 'bg-white dark:bg-gray-900/40 border-gray-200 dark:border-gray-800 shadow-sm'
                            }`}
                        >
                            <div className="flex items-center gap-2">
                                <Badge
                                    size="xs"
                                    variant={isSystem ? 'soft' : 'solid'}
                                    colorScheme={
                                        isAssistant ? 'accent' : isTool ? 'success' : 'neutral'
                                    }
                                    radius="none"
                                >
                                    {msg.role}
                                </Badge>
                            </div>
                            <div className="text-xs font-normal font-mono leading-relaxed text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words selection:bg-blue-500/30 overflow-x-hidden">
                                <FormattedContent content={msg.content || msg.parts || msg} />
                            </div>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}
