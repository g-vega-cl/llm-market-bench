interface FormattedContentProps {
    content: unknown;
}

/** Derive a stable key from part content — deterministic, no index dependency. */
function partKey(part: unknown): string {
    const str = JSON.stringify(part);
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const ch = str.charCodeAt(i);
        hash = (hash << 5) - hash + ch;
        hash |= 0;
    }
    return String(hash);
}

export function FormattedContent({ content }: FormattedContentProps) {
    if (typeof content === 'string') {
        try {
            if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
                const parsed = JSON.parse(content);
                return (
                    <pre className="font-mono text-xs font-normal leading-relaxed whitespace-pre-wrap break-all overflow-hidden m-0">
                        {JSON.stringify(parsed, null, 2)}
                    </pre>
                );
            }
        } catch (_e) {
            // not JSON
        }
        return <>{content}</>;
    }

    if (Array.isArray(content)) {
        return (
            <div className="flex flex-col gap-3">
                {content.map((part) => (
                    <div
                        key={partKey(part)}
                        className="border-l-2 border-gray-200 dark:border-gray-700 pl-3 md:pl-4 py-1"
                    >
                        {part.text && (
                            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap break-words text-xs font-normal m-0">
                                {part.text}
                            </p>
                        )}
                        {part.thought && (
                            <div className="bg-amber-50/50 dark:bg-amber-900/10 p-3 rounded-none border border-amber-100 dark:border-amber-900/20">
                                <span className="text-xs font-bold text-amber-600 dark:text-amber-500 uppercase tracking-wider block mb-1">
                                    Internal Thought
                                </span>
                                <p className="text-amber-800 dark:text-amber-200 italic font-normal text-xs break-words m-0">
                                    {part.thought}
                                </p>
                            </div>
                        )}
                        {part.function_call && (
                            <div className="bg-blue-50/50 dark:bg-blue-900/10 p-3 rounded-none border border-blue-100 dark:border-blue-900/20">
                                <span className="text-xs font-bold text-blue-600 dark:text-blue-500 uppercase tracking-wider block mb-1">
                                    Tool Call: {part.function_call.name}
                                </span>
                                <pre className="text-xs font-normal font-mono text-blue-800 dark:text-blue-300 whitespace-pre-wrap break-all overflow-hidden m-0">
                                    {JSON.stringify(part.function_call.args, null, 2)}
                                </pre>
                            </div>
                        )}
                        {part.function_response && (
                            <div className="bg-emerald-50/50 dark:bg-emerald-900/10 p-3 rounded-none border border-emerald-100 dark:border-emerald-900/20">
                                <span className="text-xs font-bold text-emerald-600 dark:text-emerald-500 uppercase tracking-wider block mb-1">
                                    Tool Response: {part.function_response.name}
                                </span>
                                <pre className="text-xs font-normal font-mono text-emerald-800 dark:text-emerald-300 whitespace-pre-wrap break-all overflow-hidden m-0">
                                    {JSON.stringify(part.function_response.response, null, 2)}
                                </pre>
                            </div>
                        )}
                        {!part.text &&
                            !part.thought &&
                            !part.function_call &&
                            !part.function_response && (
                                <pre className="text-xs font-normal font-mono whitespace-pre-wrap break-all overflow-hidden m-0">
                                    {JSON.stringify(part, null, 2)}
                                </pre>
                            )}
                    </div>
                ))}
            </div>
        );
    }

    return (
        <pre className="font-mono text-xs font-normal leading-relaxed whitespace-pre-wrap break-all overflow-hidden m-0">
            {JSON.stringify(content, null, 2)}
        </pre>
    );
}
