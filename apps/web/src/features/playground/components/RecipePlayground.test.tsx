import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RecipePlayground } from './RecipePlayground';

const navigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
    useRouter: () => ({ navigate }),
    Link: ({ children }: { children: React.ReactNode }) => <a href="#test">{children}</a>,
}));

vi.mock('../api/launch-recipe', () => ({ launchRecipeFn: vi.fn() }));
vi.mock('../api/run-requests', () => ({ submitRunRequestFn: vi.fn() }));
vi.mock('~/features/recipes/builder/compiler-api', () => ({ compileStrategyFn: vi.fn() }));

describe('RecipePlayground', () => {
    it('shows every block editor open, with no collapsible summary', () => {
        render(<RecipePlayground isAuthenticated={false} runsLeft={2} />);

        expect(screen.getByTestId('block-prompt')).toBeInTheDocument();
        expect(screen.getByTestId('block-news')).toBeInTheDocument();
        expect(screen.getByTestId('block-technicals')).toBeInTheDocument();
        expect(screen.getByTestId('block-output_format')).toBeInTheDocument();
        expect(screen.getByLabelText('Prompt text')).toBeVisible();
        expect(screen.getByLabelText('Contains Keywords (comma-separated)')).toBeVisible();
        expect(screen.getAllByRole('button', { name: /add rule/i }).length).toBeGreaterThan(0);
    });

    it('names the tools the draft will call, so an empty tool list cannot ship', () => {
        render(<RecipePlayground isAuthenticated={false} runsLeft={2} />);
        expect(screen.getByText(/get_technical_indicators/)).toBeInTheDocument();
    });

    it('replaces the draft when a scenario chip is picked', () => {
        render(<RecipePlayground isAuthenticated={false} runsLeft={2} />);

        fireEvent.click(screen.getByRole('button', { name: 'Cheap quality' }));

        expect((screen.getByLabelText('Bot name') as HTMLInputElement).value).toBe(
            'Quality Value Screener',
        );
    });

    it('sends an anonymous visitor to sign in instead of queueing', () => {
        render(<RecipePlayground isAuthenticated={false} runsLeft={2} />);

        fireEvent.click(screen.getByRole('button', { name: 'Sign in to run' }));

        expect(navigate).toHaveBeenCalledWith({ to: '/login', search: { redirect: '/' } });
    });

    it('does not offer a move control on the locked answer block', () => {
        render(<RecipePlayground isAuthenticated={false} runsLeft={2} />);
        expect(screen.queryByRole('button', { name: 'Move Answer down' })).not.toBeInTheDocument();
    });
});
