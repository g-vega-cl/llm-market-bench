import { Badge } from '@llm-market-bench/ui-design-system';

// biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
export function DataCard({ item }: { item: Record<string, any> }) {
    if (typeof item !== 'object' || item === null) {
        return (
            <div className="p-3 border border-gray-200 dark:border-gray-800 rounded-none bg-gray-50/50 dark:bg-gray-900/50 font-mono text-xs font-normal">
                {String(item)}
            </div>
        );
    }

    const entries = Object.entries(item);
    const longTextFields = entries.filter(
        ([k, v]) =>
            typeof v === 'string' &&
            (v.length > 60 || k.includes('reasoning') || k.includes('summary')),
    );
    const shortFields = entries.filter(([k, _v]) => !longTextFields.find(([lk]) => lk === k));

    return (
        <div className="p-5 rounded-none border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/40 shadow-sm hover:border-blue-500/30 transition-all duration-300 flex flex-col gap-6">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-4 items-stretch">
                {shortFields.map(([k, v]) => (
                    <div key={k} className="flex flex-col gap-1">
                        <h6 className="text-xs font-bold uppercase tracking-wider text-gray-400 m-0">
                            {k.replace(/_/g, ' ')}
                        </h6>
                        <div className="text-sm font-bold text-gray-900 dark:text-gray-100 break-words">
                            {typeof v === 'boolean' ? (
                                <Badge
                                    variant="soft"
                                    colorScheme={v ? 'success' : 'danger'}
                                    size="sm"
                                    radius="none"
                                >
                                    {v ? 'YES' : 'NO'}
                                </Badge>
                            ) : (
                                String(v)
                            )}
                        </div>
                    </div>
                ))}
            </div>
            {longTextFields.length > 0 && (
                <div className="flex flex-col gap-4 pt-4 border-t border-gray-100 dark:border-gray-800/50">
                    {longTextFields.map(([k, v]) => (
                        <div key={k} className="flex flex-col gap-2">
                            <h6 className="text-xs font-bold uppercase tracking-wider text-gray-400 m-0">
                                {k.replace(/_/g, ' ')}
                            </h6>
                            <div className="text-xs font-normal leading-relaxed text-gray-600 dark:text-gray-400 whitespace-pre-wrap bg-gray-50/50 dark:bg-gray-950/30 p-3 rounded-none border border-gray-100 dark:border-gray-800/50">
                                {String(v)}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
