import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BacktestMethodologyBlock, RecipeGuideAndQuotaBlock } from './RecipeGuideAndQuotaBlock';

describe('RecipeGuideAndQuotaBlock', () => {
    it('renders live quota counts and clear backtest vs live execution explanations', () => {
        render(
            <RecipeGuideAndQuotaBlock
                quotaStatus={{
                    tier: 'beta_starter',
                    activeBacktests: 1,
                    maxConcurrentBacktests: 1,
                    backtestsLast24h: 1,
                    dailyBacktestLimit: 2,
                    liveTurnsLast24h: 2,
                    dailyLiveTurnLimit: 3,
                    activeLiveRecipes: 1,
                    maxLiveRecipes: 1,
                    globalPendingBacktests: 4,
                    globalQueueCap: 20,
                }}
            />,
        );

        expect(screen.getByText('FREE BETA STARTER')).toBeInTheDocument();
        expect(screen.getByText(/Backtests: 1\/2 left today/i)).toBeInTheDocument();
        expect(screen.getByText(/Live Turns: 1\/3 left today/i)).toBeInTheDocument();
        expect(screen.getByText(/Scheduled Live: 1\/1/i)).toBeInTheDocument();
        expect(screen.getByText(/Global Backtest Queue: 4\/20/i)).toBeInTheDocument();
        expect(screen.getByText(/How 2-Week PIT Backtests Work/i)).toBeInTheDocument();
        expect(screen.getByText(/How Live Paper Execution Works/i)).toBeInTheDocument();
    });

    it('renders backtest methodology guide cards', () => {
        render(<BacktestMethodologyBlock />);
        expect(screen.getByText('How To Read This Backtest')).toBeInTheDocument();
        expect(screen.getByText('Point-in-Time Intraday Slots')).toBeInTheDocument();
        expect(screen.getByText('Open Positions vs Closed Trades')).toBeInTheDocument();
    });
});
