import * as React from 'react';
import { fetchLiveIntradayTape, mergeIncomingBar } from '../api/fetch-intraday-tape';
import type { LiveAgentState } from '../components/LiveAgentConsole';
import type { CandlestickBar, ChartTradeMarker } from '../components/SPYCandlestickChart';

export interface UseLiveTapeStreamOptions {
    initialBars?: CandlestickBar[];
    initialTrades?: ChartTradeMarker[];
    initialAgentState?: LiveAgentState;
    isMarketOpen?: boolean;
    streamUrl?: string;
    onRefreshTape?: () => void;
}

function parseJson<T>(raw: string): T | null {
    try {
        return JSON.parse(raw) as T;
    } catch {
        return null;
    }
}

interface StreamListeners {
    onOpen: () => void;
    onSnapshot: (data: {
        bars?: CandlestickBar[];
        technicals?: LiveAgentState['technicals'];
        agent_state?: Partial<LiveAgentState>;
    }) => void;
    onBar: (data: { bar?: CandlestickBar; technicals?: LiveAgentState['technicals'] }) => void;
    onAgentTurn: (agentState: Partial<LiveAgentState>) => void;
    onError: () => void;
}

function setupStreamListeners(es: EventSource, listeners: StreamListeners) {
    es.onopen = listeners.onOpen;
    es.onerror = listeners.onError;

    es.addEventListener('snapshot', (e: MessageEvent) => {
        const data = parseJson<{
            bars?: CandlestickBar[];
            technicals?: LiveAgentState['technicals'];
            agent_state?: Partial<LiveAgentState>;
        }>(e.data);
        if (data) listeners.onSnapshot(data);
    });

    es.addEventListener('bar', (e: MessageEvent) => {
        const data = parseJson<{
            bar?: CandlestickBar;
            technicals?: LiveAgentState['technicals'];
        }>(e.data);
        if (data) listeners.onBar(data);
    });

    es.addEventListener('agent_turn', (e: MessageEvent) => {
        const data = parseJson<{ agent_state?: Partial<LiveAgentState> }>(e.data);
        if (data?.agent_state) listeners.onAgentTurn(data.agent_state);
    });
}

function getDefaultStreamUrl(): string {
    if (typeof window !== 'undefined' && import.meta.env.VITE_ARCHIVE_DB_URL) {
        const base = import.meta.env.VITE_ARCHIVE_DB_URL.replace(/\/$/, '');
        return `${base}/api/tape/stream`;
    }
    return '/api/tape/stream';
}

export function useLiveTapeStream({
    initialBars = [],
    initialTrades = [],
    initialAgentState,
    isMarketOpen = true,
    streamUrl = getDefaultStreamUrl(),
    onRefreshTape,
}: UseLiveTapeStreamOptions) {
    const [bars, setBars] = React.useState<CandlestickBar[]>(initialBars);
    const [trades, setTrades] = React.useState<ChartTradeMarker[]>(initialTrades);
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
                    if (snapshot.trades) {
                        setTrades(snapshot.trades);
                    }
                    if (snapshot.agentState) {
                        setAgentState(snapshot.agentState);
                    }
                })
                .catch(() => {});
        }
    }, [initialBars]);

    React.useEffect(() => {
        if (initialTrades.length > 0) {
            setTrades(initialTrades);
        }
    }, [initialTrades]);

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
            if (snapshot.trades) {
                setTrades(snapshot.trades);
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

                setupStreamListeners(es, {
                    onOpen: () => setIsStreaming(true),
                    onError: () => setIsStreaming(false),
                    onSnapshot: (data) => {
                        if (Array.isArray(data.bars) && data.bars.length > 0) {
                            setBars(data.bars);
                        }
                        if (data.technicals) {
                            setAgentState((prev) =>
                                prev ? { ...prev, technicals: data.technicals } : undefined,
                            );
                        }
                        if (data.agent_state) {
                            setAgentState((prev) =>
                                prev
                                    ? { ...prev, ...data.agent_state }
                                    : (data.agent_state as LiveAgentState),
                            );
                        }
                    },
                    onBar: (data) => {
                        if (data.bar) {
                            setBars((prev) => mergeIncomingBar(prev, data.bar));
                        }
                        if (data.technicals) {
                            setAgentState((prev) =>
                                prev ? { ...prev, technicals: data.technicals } : undefined,
                            );
                        }
                    },
                    onAgentTurn: (agentState) => {
                        setAgentState((prev) =>
                            prev ? { ...prev, ...agentState } : (agentState as LiveAgentState),
                        );
                    },
                });
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
        trades,
        agentState,
        isStreaming,
        isRefreshing,
        refreshTape,
    };
}
