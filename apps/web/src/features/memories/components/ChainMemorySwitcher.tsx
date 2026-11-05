import { Badge, Button, LoadingSpinner } from '@llm-market-bench/ui-design-system';
import { useNavigate } from '@tanstack/react-router';
import * as React from 'react';
import type { Memory } from '../components/MemoriesList';

interface ChainMemorySwitcherProps {
    currentMemoryId: string;
    searchFn?: (query: string) => Promise<Memory[]>;
}

const FEATURED_TICKERS = ['TSLA', 'NVDA', 'SPY', 'AAPL', 'Macro'];

export function ChainMemorySwitcher({ currentMemoryId, searchFn }: ChainMemorySwitcherProps) {
    const navigate = useNavigate();
    const [searchQuery, setSearchQuery] = React.useState('');
    const [results, setResults] = React.useState<Memory[]>([]);
    const [isLoading, setIsLoading] = React.useState(false);
    const [isOpen, setIsOpen] = React.useState(false);
    const containerRef = React.useRef<HTMLDivElement>(null);

    const handleSearch = React.useCallback(
        async (query: string) => {
            const cleanQuery = query.trim();
            if (!cleanQuery || !searchFn) {
                setResults([]);
                setIsOpen(false);
                return;
            }

            setIsLoading(true);
            try {
                const searchResults = await searchFn(cleanQuery);
                setResults(searchResults || []);
                setIsOpen(true);
            } catch (err) {
                console.error('Failed to search memory chains:', err);
                setResults([]);
            } finally {
                setIsLoading(false);
            }
        },
        [searchFn],
    );

    const handleSelectMemory = (memoryId: string) => {
        setIsOpen(false);
        setSearchQuery('');
        if (memoryId !== currentMemoryId) {
            navigate({
                to: '/memories/chain/$memoryId',
                params: { memoryId },
            });
        }
    };

    const handleTickerClick = (ticker: string) => {
        setSearchQuery(ticker);
        handleSearch(ticker);
    };

    // Close dropdown on outside click
    React.useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div ref={containerRef} className="relative flex flex-col gap-3">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                {/* Featured Ticker Quick Switch Pills */}
                <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                        Switch Chain:
                    </span>
                    {FEATURED_TICKERS.map((ticker) => (
                        <Button
                            key={ticker}
                            size="sm"
                            variant="ghost"
                            colorScheme="neutral"
                            onClick={() => handleTickerClick(ticker)}
                            className="rounded-none text-xs font-bold"
                        >
                            ${ticker}
                        </Button>
                    ))}
                </div>

                {/* Search Bar Input */}
                <div className="relative flex-1 sm:max-w-xs">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => {
                            setSearchQuery(e.target.value);
                            handleSearch(e.target.value);
                        }}
                        onFocus={() => {
                            if (results.length > 0) setIsOpen(true);
                        }}
                        placeholder="Search another chain..."
                        className="w-full bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-white/10 rounded-none px-3 py-1.5 pl-8 pr-8 text-xs text-zinc-900 dark:text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-400 dark:focus:ring-white/20 transition-all font-sans"
                    />
                    <span className="absolute left-2.5 top-2 text-zinc-400 dark:text-zinc-500">
                        <svg
                            className="w-3.5 h-3.5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <title>Search Icon</title>
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                            />
                        </svg>
                    </span>
                    {isLoading && (
                        <span className="absolute right-2.5 top-2">
                            <LoadingSpinner size="sm" className="text-zinc-400" />
                        </span>
                    )}
                </div>
            </div>

            {/* Dropdown Results Box */}
            {isOpen && results.length > 0 && (
                <div className="absolute top-full right-0 left-0 sm:left-auto sm:w-96 z-50 mt-1 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xl max-h-72 overflow-y-auto">
                    <div className="p-2 border-b border-zinc-100 dark:border-zinc-800 text-xs font-bold text-zinc-400 uppercase tracking-wider">
                        Available Memory Chains ({results.length})
                    </div>
                    <div className="flex flex-col">
                        {results.slice(0, 10).map((mem) => {
                            const isCurrent = mem.id === currentMemoryId;
                            return (
                                <button
                                    key={mem.id}
                                    type="button"
                                    onClick={() => handleSelectMemory(mem.id)}
                                    className={`p-3 text-left border-b border-zinc-100 dark:border-zinc-800/50 hover:bg-zinc-50 dark:hover:bg-zinc-800/60 transition-colors flex flex-col gap-1 ${
                                        isCurrent ? 'bg-zinc-100/50 dark:bg-zinc-800/40' : ''
                                    }`}
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <div className="flex items-center gap-1.5 flex-wrap">
                                            {mem.metadata?.ticker && (
                                                <Badge
                                                    size="xs"
                                                    variant="soft"
                                                    colorScheme="accent"
                                                >
                                                    ${mem.metadata.ticker}
                                                </Badge>
                                            )}
                                            <span className="text-xs font-mono text-zinc-400">
                                                {mem.created_at
                                                    ? new Date(mem.created_at).toLocaleDateString()
                                                    : 'Recent'}
                                            </span>
                                        </div>
                                        {isCurrent && (
                                            <span className="text-xs font-bold text-emerald-500 font-mono">
                                                CURRENT
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-xs font-normal text-zinc-800 dark:text-zinc-200 line-clamp-2 m-0">
                                        {mem.content}
                                    </p>
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
