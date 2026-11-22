import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { CEDAR_WORLD_ID } from '../home/backdrop/voxel-world';
import { PersonalityQuizPage } from './PersonalityQuizPage';
import { PERSONALITY_QUESTIONS } from './personality-data';

vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        search,
        className,
        ...rest
    }: {
        children: React.ReactNode;
        to: string;
        search?: Record<string, string>;
        className?: string;
    }) => {
        const qs = search ? `?${new URLSearchParams(search).toString()}` : '';
        return (
            <a href={`${to}${qs}`} className={className} {...rest}>
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

describe('PersonalityQuizPage (10-question diagnostic & Cedar Sanctuary SceneStage)', () => {
    it('steps through all 10 questions with back navigation, live style updates, and reveals top-2 bots', () => {
        render(<PersonalityQuizPage initialAtmosphere="daylight" />);

        expect(screen.getByTestId('garden-backdrop')).toHaveAttribute('data-world', CEDAR_WORLD_ID);
        expect(screen.getByTestId('garden-backdrop')).toHaveAttribute(
            'data-atmosphere',
            'daylight',
        );
        expect(screen.getByTestId('personality-quiz-card')).toBeInTheDocument();
        expect(screen.getByText(PERSONALITY_QUESTIONS[0].prompt)).toBeInTheDocument();

        // Answer Question 1 -> advances to Question 2 and updates live leaning archetype hint
        fireEvent.click(
            screen.getByTestId(`quiz-option-${PERSONALITY_QUESTIONS[0].options[0].id}`),
        );
        expect(screen.getByText(PERSONALITY_QUESTIONS[1].prompt)).toBeInTheDocument();
        expect(screen.getByTestId('quiz-live-world-hint').textContent).toContain('Leaning:');

        // Navigate back to Question 1 and step forward through all 10 questions
        fireEvent.click(screen.getByRole('button', { name: /previous question/i }));
        expect(screen.getByText(PERSONALITY_QUESTIONS[0].prompt)).toBeInTheDocument();

        for (const q of PERSONALITY_QUESTIONS) {
            fireEvent.click(screen.getByTestId(`quiz-option-${q.options[0].id}`));
        }

        const result = screen.getByTestId('personality-result');
        expect(result).toBeInTheDocument();
        expect(within(result).getByTestId('axis-breakdown')).toBeInTheDocument();
        expect(within(result).getByText('#1 Best Bot Match')).toBeInTheDocument();
        expect(within(result).getByText('#2 Runner-Up Match')).toBeInTheDocument();

        const buildLinks = within(result).getAllByRole('link', { name: /build this bot/i });
        expect(buildLinks[0].getAttribute('href')).toContain('/build?idea=');

        // Retake resets back to Q1
        fireEvent.click(screen.getByTestId('retake-quiz'));
        expect(screen.getByTestId('personality-quiz-card')).toBeInTheDocument();
        expect(screen.getByText(PERSONALITY_QUESTIONS[0].prompt)).toBeInTheDocument();
    });

    it('hydrates shared ?archetype= links directly with Cedar backdrop and zero nested cards', () => {
        render(<PersonalityQuizPage initialArchetype="contrarian-diver" />);

        const canvas = screen.getByTestId('garden-backdrop');
        expect(canvas).toHaveAttribute('data-world', CEDAR_WORLD_ID);
        expect(screen.getByTestId('archetype-title')).toHaveTextContent('The Contrarian Diver');
        expect(screen.queryByTestId('apply-homepage-world')).toBeNull();

        // Design spec: zero nested .voxel-card elements inside personality-result
        const resultPlaque = screen.getByTestId('personality-result');
        expect(resultPlaque.querySelectorAll('.voxel-card')).toHaveLength(0);
    });

    it('switches cleanly to shared archetype inspect mode even after partial quiz answers', () => {
        const { rerender } = render(<PersonalityQuizPage />);
        fireEvent.click(
            screen.getByTestId(`quiz-option-${PERSONALITY_QUESTIONS[0].options[0].id}`),
        );
        expect(screen.getByText(PERSONALITY_QUESTIONS[1].prompt)).toBeInTheDocument();

        rerender(<PersonalityQuizPage initialArchetype="news-surfer" />);
        expect(screen.getByTestId('archetype-title')).toHaveTextContent('The Headline Surfer');
        expect(screen.getByTestId('garden-backdrop')).toHaveAttribute('data-world', CEDAR_WORLD_ID);
    });

    it('anchors the 5-archetype switcher at the top and keeps card badge counts & structure invariant across switches', () => {
        render(<PersonalityQuizPage initialArchetype="value-compounder" />);

        const result = screen.getByTestId('personality-result');
        const switcher = within(result).getByTestId('archetype-switcher');
        const title = within(result).getByTestId('archetype-title');

        // Switcher must precede the archetype title so buttons stay anchored at the top
        expect(
            switcher.compareDocumentPosition(title) & Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();

        const buttons = within(switcher).getAllByRole('button');
        expect(buttons).toHaveLength(5);

        for (const button of buttons) {
            fireEvent.click(button);
            const cards = within(result).getAllByTestId('bot-recommendation-card');
            expect(cards).toHaveLength(2);
            for (const card of cards) {
                expect(card.querySelectorAll('.voxel-badge')).toHaveLength(4);
                expect(card.querySelectorAll('.overflow-y-auto')).toHaveLength(0);
            }
        }

        // Design Spec §9.4: meta rows enforce flex-wrap and whitespace-nowrap fragments
        const axisPanel = within(result).getByTestId('axis-breakdown');
        expect(axisPanel.querySelectorAll('.flex-wrap').length).toBeGreaterThanOrEqual(8);
        expect(axisPanel.querySelectorAll('.whitespace-nowrap').length).toBeGreaterThanOrEqual(16);
    });

    it('preserves quiz answers across inspection, returns on self-selection, and avoids self-navigation wipes', () => {
        const syncedParams: Array<string | null> = [];
        const { rerender } = render(
            <PersonalityQuizPage
                onArchetypeSearchChange={(next) => {
                    syncedParams.push(next);
                }}
            />,
        );
        for (const q of PERSONALITY_QUESTIONS) {
            fireEvent.click(screen.getByTestId(`quiz-option-${q.options[0].id}`));
        }
        const initialTitle = screen.getByTestId('archetype-title').textContent;
        const matchedSlug = syncedParams.at(-1) as 'value-compounder' | undefined;
        expect(matchedSlug).toBeTruthy();

        // Simulate TanStack Router propagating the self-emitted search param back cleanly
        rerender(
            <PersonalityQuizPage
                initialArchetype={matchedSlug}
                onArchetypeSearchChange={(next) => {
                    syncedParams.push(next);
                }}
            />,
        );
        expect(screen.queryByTestId('return-to-quiz-match')).toBeNull();

        // Explore a different archetype without shifting switcher button count
        const switcher = screen.getByTestId('archetype-switcher');
        expect(within(switcher).getAllByRole('button')).toHaveLength(5);
        const altButton = within(switcher)
            .getAllByRole('button')
            .find((b) => b.textContent !== initialTitle);
        expect(altButton).toBeDefined();
        if (altButton) fireEvent.click(altButton);

        expect(within(switcher).getAllByRole('button')).toHaveLength(5);
        expect(screen.getByTestId('archetype-title')).toHaveTextContent(
            altButton?.textContent ?? '',
        );
        expect(screen.getByTestId('return-to-quiz-match')).toBeInTheDocument();

        // Clicking own quiz match archetype in switcher transitions back to quiz_match mode
        const selfButton = within(switcher)
            .getAllByRole('button')
            .find((b) => b.textContent === initialTitle);
        expect(selfButton).toBeDefined();
        if (selfButton) fireEvent.click(selfButton);
        expect(screen.queryByTestId('return-to-quiz-match')).toBeNull();

        // Explore again and use explicit Back to my quiz match action
        if (altButton) fireEvent.click(altButton);
        fireEvent.click(screen.getByTestId('return-to-quiz-match'));
        expect(screen.getByTestId('archetype-title')).toHaveTextContent(initialTitle ?? '');

        // External navigation to ?archetype=news-surfer then back to bare /personality resets to Q1
        rerender(<PersonalityQuizPage initialArchetype="news-surfer" />);
        expect(screen.getByTestId('archetype-title')).toHaveTextContent('The Headline Surfer');
        rerender(<PersonalityQuizPage initialArchetype={undefined} />);
        expect(screen.getByTestId('personality-quiz-card')).toBeInTheDocument();
    });
});
