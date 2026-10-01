import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DailyMetricsOverview } from './DailyMetricsOverview';

describe('DailyMetricsOverview', () => {
    it('renders all metrics cards with passed values', () => {
        render(
            <DailyMetricsOverview
                accuracyPct="65.5"
                intradayHitPct="40.0"
                correctCount={13}
                totalEvaluated={20}
                avgBrier="0.1850"
                totalPredictions={25}
                activePromptTag="daily-active-v1"
            />,
        );

        expect(screen.getByText('Directional Accuracy')).toBeInTheDocument();
        expect(screen.getByText('65.5%')).toBeInTheDocument();
        expect(screen.getByText('13 / 20 correct')).toBeInTheDocument();

        expect(screen.getByText('Intraday Target Hit (30%)')).toBeInTheDocument();
        expect(screen.getByText('40.0%')).toBeInTheDocument();

        expect(screen.getByText('Brier Calibration Score')).toBeInTheDocument();
        expect(screen.getByText('0.1850')).toBeInTheDocument();

        expect(screen.getByText('Total Predictions')).toBeInTheDocument();
        expect(screen.getByText('25')).toBeInTheDocument();

        expect(screen.getByText('Active Prompt Variant')).toBeInTheDocument();
        expect(screen.getByText('daily-active-v1')).toBeInTheDocument();
        expect(screen.getByText('🟢 ACTIVE')).toBeInTheDocument();
    });
});
