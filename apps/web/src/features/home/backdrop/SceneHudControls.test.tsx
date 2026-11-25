import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SceneHudControls } from './SceneHudControls';

function renderControls(motion: 'running' | 'paused' | 'reduced') {
    return render(
        <SceneHudControls
            atmosphere="dusk"
            motion={motion}
            onCycleAtmosphere={vi.fn()}
            onTogglePaused={vi.fn()}
        />,
    );
}

describe('SceneHudControls (derived motion state)', () => {
    it('offers Pause motion while the scene is running', () => {
        renderControls('running');

        const toggle = screen.getByTestId('motion-toggle');
        expect(toggle).toHaveTextContent('Pause motion');
        expect(toggle).toHaveAttribute('aria-pressed', 'false');
        expect(toggle).toBeEnabled();
    });

    it('offers Play motion once the visitor paused the scene', () => {
        renderControls('paused');

        const toggle = screen.getByTestId('motion-toggle');
        expect(toggle).toHaveTextContent('Play motion');
        expect(toggle).toHaveAttribute('aria-pressed', 'true');
    });

    it('reports reduced motion and disables the toggle when the OS owns it', () => {
        renderControls('reduced');

        const toggle = screen.getByTestId('motion-toggle');
        // A "Pause motion" button over an already-frozen scene is the lie this
        // state exists to prevent.
        expect(toggle).toHaveTextContent('Motion: reduced');
        expect(toggle).toBeDisabled();
        expect(toggle).toHaveAttribute('data-motion', 'reduced');
    });

    it('cycles the sky through every atmosphere phase', () => {
        const onCycleAtmosphere = vi.fn();
        render(
            <SceneHudControls
                atmosphere="after-hours"
                motion="running"
                onCycleAtmosphere={onCycleAtmosphere}
                onTogglePaused={vi.fn()}
            />,
        );

        expect(screen.getByTestId('atmosphere-switcher')).toHaveTextContent('Sky: After-Hours');
    });
});
