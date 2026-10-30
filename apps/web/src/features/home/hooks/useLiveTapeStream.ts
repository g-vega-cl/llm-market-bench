import * as React from 'react';
import { fetchLiveIntradayTape, mergeIncomingBar } from '../api/fetch-intraday-tape';
import type { LiveAgentState } from '../components/LiveAgentConsole';
import type { CandlestickBar } from '../components/SPYCandlestickChart';

export interface UseLiveTapeStreamOptions {
    initialBars?: CandlestickBar[];
    initialAgentState?: LiveAgentState;
    isMarketOpen?: boolean;
    streamUrl?: string;
    onRefreshTape?: () => void;
}

export function useLiveTapeStream({
    initialBars = [],
    initialAgentState,
    isMarketOpen = true,
    streamUrl = '/api/tape/stream',
    onRefreshTape,
}: UseLiveTapeStreamOptions) {
    const [bars, setBars] = React.useState<CandlestickBar[]>(initialBars);
    const [agentState, setAgentState] = React.useState<LiveAgentState | undefined>(
        initialAgentState,
    );
    const [isStreaming, setIsStreaming] = React.useState(false);
    const [isRefreshing, setIsRefreshing] = React.useState(false);
    const eventSourceRef = React.useRef<EventSource | null>(null);
    const hasInitialFetchedRef = React.useRef(false);

    // Initial CSR fetch if initialBars was empty
    React.useEffect(() => {
        if (initialBars.length > 0) {
            setBars(initialBars);
        } else if (!hasInitialFetchedRef.current) {
            hasInitialFetchedRef.current = true;
            fetchLiveIntradayTape()
                .then((snapshot) => {
                    if (snapshot.bars && snapshot.bars.length > 0) {
                        setBars(snapshot.bars);
                    }
                    if (snapshot.agentState) {
                        setAgentState(snapshot.agentState);
                    }
                })
                .catch(() => {});
        }
    }, [initialBars]);

    React.useEffect(() => {
        if (initialAgentState) {
            setAgentState(initialAgentState);
        }
    }, [initialAgentState]);

    // Manual refresh action
    const refreshTape = React.useCallback(async () => {
        try {
            setIsRefreshing(true);
            if (onRefreshTape) onRefreshTape();
            const snapshot = await fetchLiveIntradayTape();
            if (snapshot.bars && snapshot.bars.length > 0) {
                setBars(snapshot.bars);
            }
            if (snapshot.agentState) {
                setAgentState(snapshot.agentState);
            }
        } catch {
            // Non-blocking background error
        } finally {
            setIsRefreshing(false);
        }
    }, [onRefreshTape]);

    // SSE connection with Page Visibility sleep guard
    React.useEffect(() => {
        if (typeof window === 'undefined' || typeof EventSource === 'undefined') return;
        if (!isMarketOpen) return;

        let es: EventSource | null = null;

        const connect = () => {
            if (document.hidden) return;
            if (es) es.close();

            try {
                es = new EventSource(streamUrl);
                eventSourceRef.current = es;

                es.onopen = () => {
                    setIsStreaming(true);
                };

                es.addEventListener('snapshot', (e: MessageEvent) => {
                    try {
                        const data = JSON.parse(e.data);
                        if (Array.isArray(data.bars) && data.bars.length > 0) {
                            setBars(data.bars);
                        }
                    } catch {
                        // Malformed frame ignored
                    }
                });

                es.addEventListener('bar', (e: MessageEvent) => {
                    try {
                        const data = JSON.parse(e.data);
                        if (data.bar) {
                            setBars((prev) => mergeIncomingBar(prev, data.bar));
                        }
                    } catch {
                        // Malformed frame ignored
                    }
                });

                es.onerror = () => {
                    setIsStreaming(false);
                };
            } catch {
                setIsStreaming(false);
            }
        };

        const disconnect = () => {
            if (es) {
                es.close();
                es = null;
                eventSourceRef.current = null;
                setIsStreaming(false);
            }
        };

        const handleVisibilityChange = () => {
            if (document.hidden) {
                disconnect();
            } else {
                connect();
            }
        };

        connect();
        document.addEventListener('visibilitychange', handleVisibilityChange);

        return () => {
            disconnect();
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, [isMarketOpen, streamUrl]);

    return {
        bars,
        agentState,
        isStreaming,
        isRefreshing,
        refreshTape,
    };
}
