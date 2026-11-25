import { fireEvent, render as rtlRender, screen } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { liveOverviewData } from './overview-test-fixture';
import { RecipeBehaviorPage } from './RecipeBehaviorPage';

function render(ui: React.ReactElement) {
    return rtlRender(ui);
}

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        params,
        ...rest
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, string>;
        className?: string;
    }) => {
        let href = to;
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                href = href.replace(`$${k}`, v);
            }
        }
        return (
            <a href={href} {...rest}>
                {children}
            </a>
        );
    },
}));

beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
            matches: true,
            media: query,
            onchange: null,
            addListener: vi.fn(),
            removeListener: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(),
        })),
    });

    if (typeof globalThis.ResizeObserver === 'undefined') {
        globalThis.ResizeObserver = class ResizeObserver {
            observe() {}
            unobserve() {}
            disconnect() {}
        };
    }
});

describe('RecipeBehaviorPage', () => {
    it('renders the behaviour summary and claims its own chip', () => {
        render(<RecipeBehaviorPage data={liveOverviewData} />);

        expect(screen.getByTestId('bot-behaviors-block')).toHaveTextContent(
            'Maintaining NVDA long on data center strength.',
        );
        expect(screen.getByRole('link', { name: 'Behaviour' })).toHaveAttribute(
            'aria-current',
            'page',
        );
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
            'AI Capex Radar — Behaviour',
        );
    });

    it('explains itself instead of rendering a blank page before the first run', () => {
        render(
            <RecipeBehaviorPage
                data={{
                    ...liveOverviewData,
                    recentLiveRuns: [],
                    recentBacktests: [],
                }}
            />,
        );

        expect(screen.getByText(/Behaviours appear after the first live run/i)).toBeInTheDocument();
        expect(screen.queryByTestId('bot-behaviors-block')).not.toBeInTheDocument();
    });

    it('still renders the chip row so a visitor can leave the empty tab', () => {
        render(
            <RecipeBehaviorPage
                data={{ ...liveOverviewData, recentLiveRuns: [], recentBacktests: [] }}
            />,
        );

        fireEvent.click(screen.getByRole('link', { name: 'Performance' }));
        expect(screen.getByRole('link', { name: 'Performance' })).toHaveAttribute(
            'href',
            '/recipes/rec-live-1/performance',
        );
    });
});
