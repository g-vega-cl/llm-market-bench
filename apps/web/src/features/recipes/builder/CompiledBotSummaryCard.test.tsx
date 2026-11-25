import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { PushStrategy } from '../types';
import { CompiledBotSummaryCard } from './CompiledBotSummaryCard';

/**
 * Visibility is public by default (`strategy_recipes.is_public DEFAULT TRUE`),
 * and the builder used to say nothing about it — a user could be published to
 * the gallery and leaderboard without ever being told. These tests pin the
 * disclosure and the fact that a bot the owner took private says so instead.
 */

const strategy: PushStrategy = {
    version: '2.0-push',
    id: 'recipe-1',
    name: 'Chip momentum',
    description: 'Buys strong chips.',
    cadence: '3h',
    stages: [
        {
            id: 'stage-1',
            blocks: [{ id: 'b1', type: 'output_format' } as never],
            selected_tools: ['get_technical_indicators'],
        },
    ],
};

function renderCard(overrides: { isPublic?: boolean } = {}) {
    return render(
        <CompiledBotSummaryCard
            strategy={strategy}
            isDirty={false}
            isBusy={false}
            saveState="saved"
            saveError={null}
            isRunningBacktest={false}
            isTogglingLive={false}
            isCurrentlyScheduledLive={false}
            backtestButtonLabel="Backtest 2 weeks"
            onNameChange={vi.fn()}
            onSave={vi.fn()}
            onBacktest={vi.fn()}
            onToggleLive={vi.fn()}
            {...overrides}
        />,
    );
}

describe('CompiledBotSummaryCard visibility notice', () => {
    it('tells the owner a freshly compiled bot is public', () => {
        renderCard();
        const notice = screen.getByTestId('bot-visibility-notice');
        expect(notice.textContent).toMatch(/Public bot/i);
        expect(notice.textContent).toMatch(/gallery/i);
        expect(notice.textContent).toMatch(/My Bots/i);
    });

    it('says a private bot is private instead of claiming publication', () => {
        renderCard({ isPublic: false });
        const notice = screen.getByTestId('bot-visibility-notice');
        expect(notice.textContent).toMatch(/Private bot/i);
        expect(notice.textContent).not.toMatch(/Public bot/i);
    });
});
