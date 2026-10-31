import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../api/fetch-intraday-tape', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../api/fetch-intraday-tape')>();
    return {
        ...actual,
        fetchLiveIntradayTape: vi.fn().mockResolvedValue({
            bars: [],
            agentState: null,
            isMarketOpen: true,
        }),
    };
});

vi.mock('../api/fetch-agent-queue', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../api/fetch-agent-queue')>();
    return {
        ...actual,
        fetchAgentQueueStatus: vi.fn().mockResolvedValue({
            pendingCount: 0,
            latestAnswered: null,
        }),
    };
});

import { fetchLiveIntradayTape } from '../api/fetch-intraday-tape';
import { LiveAgentConsole } from './LiveAgentConsole';

const mockBars = [
    {
        time: '2026-10-29T14:00:00Z',
        open: 580.0,
        high: 581.0,
        low: 579.5,
        close: 580.5,
        volume: 10000,
    },
];

const mockAgentState = {
    action: 'BUY' as const,
    conviction: 82,
    thought: 'SPY bounced cleanly off the 15m VWAP with volume expansion.',
    marketDirection: 'BULLISH' as const,
    sentimentLabel: 'Accumulating Dips',
    modelUsed: 'Strata Orca',
    lastUpdated: '14:25 ET',
    technicals: {
        vwap: 580.2,
        rsi_14: 58.4,
        trend: 'BULLISH',
    },
    memoriesConsulted: ['Morning Dip Absorption #82'],
};

describe('LiveAgentConsole', () => {
    it('renders autonomous trader title and status badges', () => {
        render(
            <LiveAgentConsole bars={mockBars} agentState={mockAgentState} isMarketOpen={true} />,
        );
        expect(screen.getByText(/24\/7 Autonomous SPY Trader/i)).toBeInTheDocument();
        expect(screen.getByText(/LIVE SESSION/i)).toBeInTheDocument();
        expect(screen.getAllByText(/BULLISH/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText(/Accumulating Dips/i)).toBeInTheDocument();
    });

    it('renders thought trace and technical indicators', () => {
        render(
            <LiveAgentConsole bars={mockBars} agentState={mockAgentState} isMarketOpen={true} />,
        );
        expect(screen.getByText(/SPY bounced cleanly off the 15m VWAP/i)).toBeInTheDocument();
        expect(screen.getByText(/VWAP:/i)).toBeInTheDocument();
        expect(screen.getByText(/\$580.20/i)).toBeInTheDocument();
        expect(screen.getByText(/RSI:/i)).toBeInTheDocument();
        expect(screen.getByText(/58.4/i)).toBeInTheDocument();
    });

    it('renders chat queue with sign in CTA when user is not authenticated', () => {
        render(
            <LiveAgentConsole
                bars={mockBars}
                agentState={mockAgentState}
                isMarketOpen={true}
                currentUser={null}
            />,
        );
        expect(screen.getByText(/Audience Interactive Queue/i)).toBeInTheDocument();
        expect(screen.getByText(/Sign In to Queue/i)).toBeInTheDocument();
    });

    it('renders chat queue input and 500-char limit when user is authenticated', () => {
        render(
            <LiveAgentConsole
                bars={mockBars}
                agentState={mockAgentState}
                isMarketOpen={true}
                currentUser={{ id: 'usr-1', email: 'trader@example.com' }}
            />,
        );
        expect(screen.getByText(/Audience Interactive Queue/i)).toBeInTheDocument();
        expect(
            screen.getByPlaceholderText(/Ask a question or thesis hypothesis \(max 500 chars\)/i),
        ).toBeInTheDocument();
        expect(screen.getByText(/0\/500/i)).toBeInTheDocument();
        expect(screen.getByText(/Logged in as analyst/i)).toBeInTheDocument();
    });

    it('displays closed banner when market is closed', () => {
        render(
            <LiveAgentConsole bars={mockBars} agentState={mockAgentState} isMarketOpen={false} />,
        );
        expect(screen.getByText(/MARKET CLOSED/i)).toBeInTheDocument();
    });

    it('does not start a background interval polling fetchLiveIntradayTape', () => {
        vi.useFakeTimers();
        const mockFetch = vi.mocked(fetchLiveIntradayTape);
        mockFetch.mockClear();

        render(
            <LiveAgentConsole bars={mockBars} agentState={mockAgentState} isMarketOpen={true} />,
        );

        expect(mockFetch).not.toHaveBeenCalled();

        // Advance 60 seconds (what would have been 3 intervals under 20s polling)
        act(() => {
            vi.advanceTimersByTime(60000);
        });

        expect(mockFetch).not.toHaveBeenCalled();
        vi.useRealTimers();
    });

    it('triggers manual refresh when Refresh Tape button is clicked', async () => {
        const mockFetch = vi.mocked(fetchLiveIntradayTape);
        mockFetch.mockClear();
        const onRefreshTape = vi.fn();

        render(
            <LiveAgentConsole
                bars={mockBars}
                agentState={mockAgentState}
                isMarketOpen={true}
                onRefreshTape={onRefreshTape}
            />,
        );

        const refreshBtn = screen.getByRole('button', { name: /refresh/i });
        await act(async () => {
            fireEvent.click(refreshBtn);
        });

        expect(onRefreshTape).toHaveBeenCalledTimes(1);
        expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('renders clean technicals row without Ref tags and displays memory vault footer link', () => {
        render(
            <LiveAgentConsole bars={mockBars} agentState={mockAgentState} isMarketOpen={true} />,
        );
        expect(screen.queryByText(/^Ref:/i)).not.toBeInTheDocument();
        expect(screen.getByText(/Autonomous intraday paper execution/i)).toBeInTheDocument();
        expect(screen.getByText(/Grounded in 1 memory reference/i)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /Memory Vault/i })).toHaveAttribute(
            'href',
            '/memories',
        );
        expect(screen.getByRole('link', { name: /Lab/i })).toHaveAttribute('href', '/lab');
    });
});
