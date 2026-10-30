import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
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
});
