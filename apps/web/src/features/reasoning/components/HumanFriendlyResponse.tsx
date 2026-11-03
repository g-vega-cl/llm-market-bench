import { Button } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { DataCard } from './DataCard';

export function HumanFriendlyResponse({ response }: { response: unknown }) {
    const [activeTab, setActiveTab] = React.useState('RAW');

    if (!response || typeof response !== 'object') {
        return (
            <section className="flex flex-col gap-4">
                <div className="flex items-center gap-3">
                    <h4 className="text-sm font-bold text-gray-400 uppercase tracking-wider m-0">
                        Output Schema
                    </h4>
                    <div className="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-800 to-transparent" />
                </div>
                <div className="relative group/raw">
                    <pre className="p-4 bg-zinc-950 text-sky-300 rounded-none text-xs font-normal font-mono whitespace-pre-wrap break-all overflow-hidden border border-zinc-800 shadow-sm leading-relaxed m-0">
                        {JSON.stringify(response, null, 2)}
                    </pre>
                    <Button
                        size="sm"
                        variant="glass"
                        colorScheme="neutral"
                        className="absolute top-2 right-2 opacity-0 group-hover/raw:opacity-100 transition-opacity rounded-none text-sm font-bold"
                        onClick={() =>
                            navigator.clipboard.writeText(JSON.stringify(response, null, 2))
                        }
                    >
                        Copy
                    </Button>
                </div>
            </section>
        );
    }

    const resp = response as Record<string, unknown>;
    const keys = Object.keys(resp);
    const displayedKeys = [...keys, 'RAW'];

    return (
        <section className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                    <h4 className="text-sm font-bold text-gray-400 uppercase tracking-wider whitespace-nowrap m-0">
                        Output Schema
                    </h4>
                    <div className="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-800 to-transparent min-w-[20px]" />
                </div>
                <div className="flex gap-1 p-1 bg-zinc-100 dark:bg-zinc-900 rounded-none border border-zinc-200 dark:border-zinc-800 shadow-inner overflow-x-auto">
                    {displayedKeys.map((key) => (
                        <Button
                            key={key}
                            size="sm"
                            variant={activeTab === key ? 'solid' : 'ghost'}
                            colorScheme={activeTab === key ? 'accent' : 'neutral'}
                            onClick={() => setActiveTab(key)}
                            className="rounded-none text-sm font-bold"
                        >
                            {key.replace(/_/g, ' ')}
                        </Button>
                    ))}
                </div>
            </div>

            <div>
                {activeTab === 'RAW' ? (
                    <div className="relative group/raw">
                        <pre className="p-4 bg-zinc-950 text-sky-300 rounded-none text-xs font-normal font-mono whitespace-pre-wrap break-all overflow-hidden border border-zinc-800 shadow-sm leading-relaxed m-0">
                            {JSON.stringify(response, null, 2)}
                        </pre>
                        <Button
                            size="sm"
                            variant="glass"
                            colorScheme="neutral"
                            className="absolute top-3 right-3 opacity-0 group-hover/raw:opacity-100 transition-all rounded-none text-sm font-bold"
                            onClick={() =>
                                navigator.clipboard.writeText(JSON.stringify(response, null, 2))
                            }
                        >
                            Copy JSON
                        </Button>
                    </div>
                ) : (
                    <div className="animate-slow-fade">
                        <ResponseDataView value={resp[activeTab]} label={activeTab} />
                    </div>
                )}
            </div>
        </section>
    );
}

function ResponseDataView({ value, label }: { value: unknown; label: string }) {
    if (Array.isArray(value)) {
        return (
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4 items-stretch">
                {value.map((item, i) => (
                    <DataCard key={i} item={item} />
                ))}
                {value.length === 0 && (
                    <p className="text-gray-500 italic text-xs font-normal m-0">Empty list.</p>
                )}
            </div>
        );
    }

    if (typeof value === 'object' && value !== null) {
        return <DataCard item={value} />;
    }

    const isLongText = typeof value === 'string' && value.length > 100;

    return (
        <div
            className={`p-4 rounded-none border bg-white dark:bg-gray-900/40 border-gray-200 dark:border-gray-800 shadow-sm flex flex-col gap-2 ${
                isLongText ? 'col-span-full' : ''
            }`}
        >
            <h5 className="text-xs font-bold uppercase tracking-wider text-gray-400 m-0">
                {label.replace(/_/g, ' ')}
            </h5>
            <div
                className={`text-xs ${
                    isLongText
                        ? 'leading-relaxed text-gray-700 dark:text-gray-300 font-normal'
                        : 'font-bold text-gray-900 dark:text-white'
                }`}
            >
                {String(value)}
            </div>
        </div>
    );
}
