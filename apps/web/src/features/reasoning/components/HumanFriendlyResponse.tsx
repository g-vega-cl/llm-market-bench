import { Button } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { DataCard } from './DataCard';

export function HumanFriendlyResponse({ response }: { response: any }) {
    const [activeTab, setActiveTab] = React.useState('RAW');

    if (!response || typeof response !== 'object') {
        return (
            <section>
                <div className="flex items-center gap-2 md:gap-4 mb-4 md:mb-6">
                    <h4 className="text-[9px] md:text-[10px] font-black text-gray-400 uppercase tracking-[0.15em] md:tracking-[0.2em]">
                        Output Schema
                    </h4>
                    <div className="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-800 to-transparent" />
                </div>
                <div className="relative group/raw">
                    <pre className="p-4 md:p-8 bg-[#0D0D10] text-[#7DD3FC] rounded-xl md:rounded-[2.5rem] text-[10px] md:text-[11px] font-mono whitespace-pre-wrap break-all overflow-hidden border border-white/5 shadow-2xl leading-relaxed">
                        {JSON.stringify(response, null, 2)}
                    </pre>
                    <Button
                        size="sm"
                        variant="glass"
                        colorScheme="neutral"
                        className="absolute top-2 right-2 md:top-4 md:right-4 opacity-0 group-hover/raw:opacity-100 transition-opacity"
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

    const keys = Object.keys(response);
    const displayedKeys = [...keys, 'RAW'];

    return (
        <section>
            <div className="flex items-center justify-between gap-2 md:gap-4 mb-4 md:mb-6">
                <div className="flex items-center gap-2 md:gap-4 flex-1 min-w-0">
                    <h4 className="text-[9px] md:text-[10px] font-black text-gray-400 uppercase tracking-[0.15em] md:tracking-[0.2em] whitespace-nowrap">
                        Output Schema
                    </h4>
                    <div className="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-800 to-transparent min-w-[20px]" />
                </div>
                <div className="flex gap-0.5 md:gap-1 p-0.5 md:p-1 bg-gray-100 dark:bg-gray-900 rounded-lg md:rounded-xl border border-gray-200 dark:border-gray-800 shadow-inner overflow-x-auto">
                    {displayedKeys.map((key) => (
                        <Button
                            key={key}
                            size="sm"
                            variant={activeTab === key ? 'solid' : 'ghost'}
                            colorScheme={activeTab === key ? 'accent' : 'neutral'}
                            onClick={() => setActiveTab(key)}
                        >
                            {key.replace(/_/g, ' ')}
                        </Button>
                    ))}
                </div>
            </div>

            <div className="mt-3 md:mt-4">
                {activeTab === 'RAW' ? (
                    <div className="relative group/raw">
                        <pre className="p-4 md:p-8 bg-[#0D0D10] text-[#7DD3FC] rounded-xl md:rounded-[2.5rem] text-[10px] md:text-[11px] font-mono whitespace-pre-wrap break-all overflow-hidden border border-white/5 shadow-2xl leading-relaxed thought-step-glow">
                            {JSON.stringify(response, null, 2)}
                        </pre>
                        <Button
                            size="sm"
                            variant="glass"
                            colorScheme="neutral"
                            className="absolute top-3 right-3 md:top-6 md:right-6 opacity-0 group-hover/raw:opacity-100 transition-all active:scale-95"
                            onClick={() =>
                                navigator.clipboard.writeText(JSON.stringify(response, null, 2))
                            }
                        >
                            Copy JSON
                        </Button>
                    </div>
                ) : (
                    <div className="animate-slow-fade">
                        <ResponseDataView value={response[activeTab]} label={activeTab} />
                    </div>
                )}
            </div>
        </section>
    );
}

function ResponseDataView({ value, label }: { value: any; label: string }) {
    if (Array.isArray(value)) {
        return (
            <div className="grid grid-cols-1 gap-3 md:gap-4">
                {value.map((item, i) => (
                    <DataCard key={i} item={item} />
                ))}
                {value.length === 0 && (
                    <p className="text-gray-500 italic text-[11px] md:text-xs">Empty list.</p>
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
            className={`p-4 md:p-6 rounded-xl md:rounded-[1.5rem] border bg-white dark:bg-gray-900/40 border-gray-200 dark:border-gray-800 shadow-sm ${
                isLongText ? 'col-span-full' : ''
            }`}
        >
            <h5 className="text-[8px] md:text-[9px] font-black uppercase tracking-widest text-gray-400 mb-1.5 md:mb-2">
                {label.replace(/_/g, ' ')}
            </h5>
            <div
                className={`text-xs md:text-sm ${
                    isLongText
                        ? 'leading-relaxed text-gray-700 dark:text-gray-300'
                        : 'font-bold text-gray-900 dark:text-white'
                }`}
            >
                {String(value)}
            </div>
        </div>
    );
}
