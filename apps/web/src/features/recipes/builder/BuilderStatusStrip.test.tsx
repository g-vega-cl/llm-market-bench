import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BuilderStatusStrip } from './BuilderStatusStrip';

describe('BuilderStatusStrip', () => {
    it('is always mounted as a live status region, even when idle', () => {
        render(<BuilderStatusStrip phase="idle" />);

        expect(screen.getByTestId('builder-status')).toBeInTheDocument();
        expect(screen.getByRole('status')).toHaveTextContent(/one sentence is enough/i);
        expect(screen.getByText('READY')).toBeInTheDocument();
    });

    it('keeps the ticking clock out of the live region so it is not announced every second', () => {
        render(<BuilderStatusStrip phase="compiling" elapsedMs={3000} />);

        const live = screen.getByTestId('builder-status-text');
        expect(live).toHaveAttribute('aria-live', 'polite');
        expect(live).toHaveTextContent(/^asking the model, then validating the recipe$/);

        const clock = screen.getByTestId('builder-status-clock');
        expect(clock).toHaveAttribute('aria-hidden', 'true');
        expect(clock).toHaveTextContent('3s');
    });

    it('admits the provider is slow once the wait passes the threshold', () => {
        render(<BuilderStatusStrip phase="compiling" elapsedMs={14000} />);

        expect(screen.getByTestId('builder-status-text')).toHaveTextContent(
            /the free model is slow right now/i,
        );
        expect(screen.getByTestId('builder-status-clock')).toHaveTextContent('14s');
    });

    it('reports alignment state clearly so the user knows to pick options', () => {
        render(<BuilderStatusStrip phase="align" />);

        expect(screen.getByText('ALIGNING STRATEGY')).toBeInTheDocument();
        expect(screen.getByRole('status')).toHaveTextContent(/build final bot/i);
    });

    it('reports a failure with a way forward instead of staying blank', () => {
        render(<BuilderStatusStrip phase="error" />);

        expect(screen.getByText('FAILED')).toBeInTheDocument();
        expect(screen.getByText(/try again/i)).toBeInTheDocument();
    });

    it('lets the workspace describe a background backtest run', () => {
        render(
            <BuilderStatusStrip
                phase="ready"
                label="BACKTEST RUNNING"
                tone="accent"
                detail="Running · 41% — you can keep editing while it works."
            />,
        );

        expect(screen.getByText('BACKTEST RUNNING')).toBeInTheDocument();
        expect(screen.getByText(/Running · 41%/)).toBeInTheDocument();
    });

    it('wraps its text row so a long detail cannot push the strip sideways (design-spec §9)', () => {
        render(<BuilderStatusStrip phase="ready" detail="Draft not saved yet" />);

        expect(screen.getByTestId('builder-status')).toHaveClass('flex-wrap', 'min-w-0');
        expect(screen.getByTestId('builder-status-text')).toHaveClass('min-w-0', 'break-words');
    });
});
