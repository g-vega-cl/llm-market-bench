import * as React from 'react';

interface FormattedContentProps {
    content: any;
}

export function FormattedContent({ content }: FormattedContentProps) {
    if (typeof content === 'string') {
        try {
            if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
                const parsed = JSON.parse(content);
                return (
                    <pre className="font-mono text-[10px] md:text-[11px] leading-relaxed whitespace-pre-wrap break-all overflow-hidden">
                        {JSON.stringify(parsed, null, 2)}
                    </pre>
                );
            }
        } catch (e) {
            // not JSON
        }
        return <>{content}</>;
    }

    if (Array.isArray(content)) {
        return (
            <div className="space-y-3 md:space-y-4">
                {content.map((part, i) => (
                    <div
                        key={i}
                        className="border-l-2 border-gray-200 dark:border-gray-700 pl-3 md:pl-4 py-0.5 md:py-1"
                    >
                        {part.text && (
                            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words text-[11px] md:text-sm">
                                {part.text}
                            </p>
                        )}
                        {part.thought && (
                            <div className="bg-amber-50/50 dark:bg-amber-900/10 p-2 md:p-3 rounded-lg md:rounded-xl border border-amber-100 dark:border-amber-900/20">
                                <span className="text-[8px] md:text-[9px] font-black text-amber-600 dark:text-amber-500 uppercase tracking-widest block mb-0.5 md:mb-1">
                                    Internal Thought
                                </span>
                                <p className="text-amber-800 dark:text-amber-200 italic font-light text-[11px] md:text-sm break-words">
                                    {part.thought}
                                </p>
                            </div>
                        )}
                        {part.function_call && (
                            <div className="bg-blue-50/50 dark:bg-blue-900/10 p-2 md:p-3 rounded-lg md:rounded-xl border border-blue-100 dark:border-blue-900/20">
                                <span className="text-[8px] md:text-[9px] font-black text-blue-600 dark:text-blue-500 uppercase tracking-widest block mb-0.5 md:mb-1">
                                    Tool Call: {part.function_call.name}
                                </span>
                                <pre className="text-[9px] md:text-[10px] font-mono text-blue-800 dark:text-blue-300 whitespace-pre-wrap break-all overflow-hidden">
                                    {JSON.stringify(part.function_call.args, null, 2)}
                                </pre>
                            </div>
                        )}
                        {part.function_response && (
                            <div className="bg-emerald-50/50 dark:bg-emerald-900/10 p-2 md:p-3 rounded-lg md:rounded-xl border border-emerald-100 dark:border-emerald-900/20">
                                <span className="text-[8px] md:text-[9px] font-black text-emerald-600 dark:text-emerald-500 uppercase tracking-widest block mb-0.5 md:mb-1">
                                    Tool Response: {part.function_response.name}
                                </span>
                                <pre className="text-[9px] md:text-[10px] font-mono text-emerald-800 dark:text-emerald-300 whitespace-pre-wrap break-all overflow-hidden">
                                    {JSON.stringify(part.function_response.response, null, 2)}
                                </pre>
                            </div>
                        )}
                        {!part.text &&
                            !part.thought &&
                            !part.function_call &&
                            !part.function_response && (
                                <pre className="text-[9px] md:text-[10px] font-mono whitespace-pre-wrap break-all overflow-hidden">
                                    {JSON.stringify(part, null, 2)}
                                </pre>
                            )}
                    </div>
                ))}
            </div>
        );
    }

    return (
        <pre className="font-mono text-[10px] md:text-[11px] leading-relaxed whitespace-pre-wrap break-all overflow-hidden">
            {JSON.stringify(content, null, 2)}
        </pre>
    );
}
