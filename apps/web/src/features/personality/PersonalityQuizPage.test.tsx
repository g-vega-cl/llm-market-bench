import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { WORLD_STORAGE_KEY } from '../home/backdrop/world-storage';
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

beforeEach(() => {
    window.localStorage.clear();
});

describe('PersonalityQuizPage (10-question diagnostic & voxel world matcher)', () => {
    it('steps through all 10 questions with back navigation, live world updates, and reveals top-2 bots', () => {
        render(<PersonalityQuizPage />);

        expect(screen.getByTestId('personality-quiz-card')).toBeInTheDocument();
        expect(screen.getByText(PERSONALITY_QUESTIONS[0].prompt)).toBeInTheDocument();

        // Answer Question 1 -> advances to Question 2 and updates live leaning world hint
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

    it('hydrates shared ?archetype= links directly with matching world and saves homepage world preference', () => {
        render(<PersonalityQuizPage initialArchetype="contrarian-diver" />);

        const canvas = screen.getByTestId('garden-backdrop');
        expect(canvas).toHaveAttribute('data-world', 'bioluminescent-reef');
        expect(canvas).toHaveAttribute('data-particle-mode', 'spores');
        expect(screen.getByTestId('archetype-title')).toHaveTextContent('The Contrarian Diver');

        fireEvent.click(screen.getByTestId('apply-homepage-world'));
        expect(window.localStorage.getItem(WORLD_STORAGE_KEY)).toBe('bioluminescent-reef');

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
        expect(screen.getByTestId('garden-backdrop')).toHaveAttribute('data-world', 'magma-forge');
    });
});
