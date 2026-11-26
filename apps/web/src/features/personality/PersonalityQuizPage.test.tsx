import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { PersonalityQuizPage } from './PersonalityQuizPage';
import { type ArchetypeId, PERSONALITY_QUESTIONS, QUIZ_ACTS } from './personality-data';
import { QUIZ_WORST_CASE } from './quiz-worst-case';

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

/** Answers every question with option A, stepping through each act checkpoint. */
function answerAll(): void {
    for (const [index, q] of PERSONALITY_QUESTIONS.entries()) {
        fireEvent.click(screen.getByTestId(`quiz-option-${q.options[0].id}`));
        if ((index + 1) % 4 === 0 && index < PERSONALITY_QUESTIONS.length - 1) {
            fireEvent.click(screen.getByTestId('continue-act'));
        }
    }
}

describe('PersonalityQuizPage (16-question diagnostic & Cedar Sanctuary SceneStage)', () => {
    it('steps through all 16 questions with back navigation, live style updates, and reveals top-2 bots', () => {
        render(<PersonalityQuizPage initialAtmosphere="daylight" />);

        expect(screen.getByTestId('personality-backdrop')).toHaveAttribute(
            'data-world',
            'personality-compass',
        );
        expect(screen.getByTestId('personality-backdrop')).toHaveAttribute(
            'data-atmosphere',
            'daylight',
        );
        expect(screen.queryByTestId('garden-backdrop')).toBeNull();
        expect(screen.getByTestId('personality-quiz-card')).toBeInTheDocument();
        expect(
            within(screen.getByTestId('personality-quiz-card')).getByRole('heading', {
                level: 2,
                name: PERSONALITY_QUESTIONS[0].prompt,
            }),
        ).toBeInTheDocument();

        // Answer Question 1 -> advances to Question 2. No letter is revealed yet:
        // the first act is not complete, so the hint falls back to its default.
        fireEvent.click(
            screen.getByTestId(`quiz-option-${PERSONALITY_QUESTIONS[0].options[0].id}`),
        );
        expect(
            within(screen.getByTestId('personality-quiz-card')).getByRole('heading', {
                level: 2,
                name: PERSONALITY_QUESTIONS[1].prompt,
            }),
        ).toBeInTheDocument();
        expect(screen.getByTestId('quiz-live-world-hint').textContent).toBe(
            'Scoring 4 trading axes',
        );

        // Navigate back to Question 1 and step forward through all 16 questions,
        // checking that the first completed act reveals exactly one letter.
        fireEvent.click(screen.getByRole('button', { name: /previous question/i }));
        expect(
            within(screen.getByTestId('personality-quiz-card')).getByRole('heading', {
                level: 2,
                name: PERSONALITY_QUESTIONS[0].prompt,
            }),
        ).toBeInTheDocument();

        for (const [index, q] of PERSONALITY_QUESTIONS.entries()) {
            fireEvent.click(screen.getByTestId(`quiz-option-${q.options[0].id}`));
            if (index === 2) {
                // Three of four horizon probes are in: still no letter revealed.
                expect(screen.getByTestId('quiz-live-world-hint').textContent).toBe(
                    'Scoring 4 trading axes',
                );
            }
            if ((index + 1) % 4 === 0 && index < PERSONALITY_QUESTIONS.length - 1) {
                const checkpoint = screen.getByTestId('act-checkpoint');
                expect(checkpoint).toBeInTheDocument();
                expect(checkpoint.textContent).toContain('complete');
                expect(screen.queryByTestId('personality-quiz-card')).toBeNull();
                fireEvent.click(screen.getByTestId('continue-act'));
                expect(screen.getByTestId('personality-quiz-card')).toBeInTheDocument();
            }
        }

        const result = screen.getByTestId('personality-result');
        expect(result).toBeInTheDocument();
        expect(within(result).getByTestId('axis-breakdown')).toBeInTheDocument();
        expect(within(result).getByText('Your best match')).toBeInTheDocument();
        expect(within(result).getByTestId('neighbour-type')).toBeInTheDocument();

        const buildLinks = within(result).getAllByRole('link', { name: /build this bot/i });
        expect(buildLinks[0].getAttribute('href')).toContain('/build?idea=');

        // Retake resets back to Q1
        fireEvent.click(screen.getByTestId('retake-quiz'));
        expect(screen.getByTestId('personality-quiz-card')).toBeInTheDocument();
        expect(
            within(screen.getByTestId('personality-quiz-card')).getByRole('heading', {
                level: 2,
                name: PERSONALITY_QUESTIONS[0].prompt,
            }),
        ).toBeInTheDocument();
    });

    it('shifts the act landmark without moving the sky or the stage (zero CLS)', () => {
        render(<PersonalityQuizPage initialAtmosphere="daylight" />);

        const stage = document.querySelector('[data-slot="scene-stage"]') as HTMLElement;
        expect(stage).toBeInstanceOf(HTMLElement);
        const before = stage.getBoundingClientRect();

        const backdrop = screen.getByTestId('personality-backdrop');
        expect(backdrop).toHaveAttribute('data-act', '0');
        expect(backdrop).toHaveAttribute('data-atmosphere', 'daylight');

        // Close Act 1: answer Q1-Q4, the checkpoint plaque shows and the
        // backdrop still lights the act that just settled.
        for (let i = 0; i < 4; i += 1) {
            fireEvent.click(
                screen.getByTestId(`quiz-option-${PERSONALITY_QUESTIONS[i].options[0].id}`),
            );
        }
        expect(screen.getByTestId('act-checkpoint')).toBeInTheDocument();
        expect(backdrop).toHaveAttribute('data-act', '0');

        // Continue into Act 2: backdrop lights Act 2, sky untouched, stage box unchanged.
        fireEvent.click(screen.getByTestId('continue-act'));
        expect(backdrop).toHaveAttribute('data-act', '1');
        expect(backdrop).toHaveAttribute('data-atmosphere', 'daylight');

        const after = stage.getBoundingClientRect();
        expect(after.width).toBeCloseTo(before.width, 0);
        expect(after.height).toBeCloseTo(before.height, 0);
    });

    it('mounts an inert, aria-hidden height sizer alongside mutually exclusive quiz and checkpoint cards', () => {
        render(<PersonalityQuizPage initialAtmosphere="daylight" />);

        const sizer = screen.getByTestId('quiz-height-sizer');
        expect(sizer).toHaveAttribute('aria-hidden', 'true');
        expect(sizer).toHaveAttribute('inert');
        // Active card owns the sole interactive buttons and prompt heading.
        expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(1);
        const quizCard = screen.getByTestId('personality-quiz-card');
        expect(quizCard).toBeInTheDocument();
        expect(screen.queryByTestId('act-checkpoint')).toBeNull();
        expect(quizCard.querySelectorAll('.flex-wrap').length).toBeGreaterThanOrEqual(3);
        expect(quizCard.querySelectorAll('.whitespace-nowrap').length).toBeGreaterThanOrEqual(2);

        for (let i = 0; i < 4; i += 1) {
            fireEvent.click(
                screen.getByTestId(`quiz-option-${PERSONALITY_QUESTIONS[i].options[0].id}`),
            );
        }

        const checkpoint = screen.getByTestId('act-checkpoint');
        expect(checkpoint).toBeInTheDocument();
        expect(screen.queryByTestId('personality-quiz-card')).toBeNull();
        expect(screen.getByTestId('quiz-height-sizer')).toBeInTheDocument();
        expect(checkpoint.querySelectorAll('.flex-wrap').length).toBeGreaterThanOrEqual(3);
        expect(checkpoint.querySelectorAll('.whitespace-nowrap').length).toBeGreaterThanOrEqual(4);
    });

    it('lights all four landmarks on the result screen', () => {
        render(<PersonalityQuizPage initialAtmosphere="dusk" />);
        answerAll();

        const backdrop = screen.getByTestId('personality-backdrop');
        expect(backdrop).toHaveAttribute('data-act', 'result');
        expect(screen.queryByTestId('garden-backdrop')).toBeNull();
    });

    it('pins the answers block position: the header, context and prompt rows reserve their longest copy', () => {
        render(<PersonalityQuizPage initialAtmosphere="daylight" />);

        const card = screen.getByTestId('personality-quiz-card');
        const pinned = [
            'quiz-row-sizer-header',
            'quiz-row-sizer-context',
            'quiz-row-sizer-prompt',
        ].map((id) => within(card).getByTestId(id));

        for (const row of pinned) {
            expect(row).toHaveAttribute('aria-hidden', 'true');
            expect(row).toHaveAttribute('inert');
            expect(row).toHaveClass('invisible', 'col-start-1', 'row-start-1');
            // The hidden reservation and the live row share one grid cell, so the
            // row is always as tall as the longest copy it can ever show.
            const cell = row.parentElement as HTMLElement;
            expect(cell.children).toHaveLength(2);
            expect(cell.children[1]).toHaveClass('col-start-1', 'row-start-1');
        }

        const [headerRow, contextRow, promptRow] = pinned;
        expect(promptRow.textContent).toBe(QUIZ_WORST_CASE.prompt);
        expect(headerRow.textContent).toContain(QUIZ_WORST_CASE.actTitle);
        expect(contextRow.textContent).toContain(QUIZ_WORST_CASE.context);
        expect(contextRow.textContent).toContain(`/ ${String(PERSONALITY_QUESTIONS.length)}`);

        // The reservation must be an upper bound for every question and act, or a
        // new/longer string would silently re-introduce the jump it exists to stop.
        for (const question of PERSONALITY_QUESTIONS) {
            expect(QUIZ_WORST_CASE.prompt.length).toBeGreaterThanOrEqual(question.prompt.length);
            expect(QUIZ_WORST_CASE.context.length).toBeGreaterThanOrEqual(question.context.length);
            question.options.forEach((option, slot) => {
                const reservation = QUIZ_WORST_CASE.options[slot];
                expect(option.label.length).toBeLessThanOrEqual(reservation.label.length);
                expect(option.detail.length).toBeLessThanOrEqual(reservation.detail.length);
            });
        }
        for (const act of QUIZ_ACTS) {
            expect(QUIZ_WORST_CASE.actTitle.length).toBeGreaterThanOrEqual(act.title.length);
        }

        // The act checkpoint reuses the same reserved header so the divider and
        // footer stay where the question card put them.
        for (let i = 0; i < 4; i += 1) {
            fireEvent.click(
                screen.getByTestId(`quiz-option-${PERSONALITY_QUESTIONS[i].options[0].id}`),
            );
        }
        const plaque = screen.getByTestId('act-checkpoint');
        const plaqueHeader = within(plaque).getByTestId('quiz-row-sizer-header');
        expect(plaqueHeader).toHaveAttribute('aria-hidden', 'true');
        expect(plaqueHeader.textContent).toContain(QUIZ_WORST_CASE.actTitle);
    });

    it('hydrates shared ?archetype= links directly with Cedar backdrop and zero nested cards', () => {
        render(<PersonalityQuizPage initialArchetype="contrarian-diver" />);

        const backdrop = screen.getByTestId('personality-backdrop');
        expect(backdrop).toHaveAttribute('data-world', 'personality-compass');
        expect(screen.getByTestId('archetype-title')).toHaveTextContent('The Contrarian Diver');
        expect(screen.queryByTestId('apply-homepage-world')).toBeNull();

        // Share route: the page heading names the same archetype as the document title
        expect(
            screen.getByRole('heading', { level: 1, name: /the contrarian diver/i }),
        ).toHaveClass('sr-only');

        // Design spec: zero nested .voxel-card elements inside personality-result
        const resultPlaque = screen.getByTestId('personality-result');
        expect(resultPlaque.querySelectorAll('.voxel-card')).toHaveLength(0);
    });

    it('switches cleanly to shared archetype inspect mode even after partial quiz answers', () => {
        const { rerender } = render(<PersonalityQuizPage />);
        fireEvent.click(
            screen.getByTestId(`quiz-option-${PERSONALITY_QUESTIONS[0].options[0].id}`),
        );
        expect(
            within(screen.getByTestId('personality-quiz-card')).getByRole('heading', {
                level: 2,
                name: PERSONALITY_QUESTIONS[1].prompt,
            }),
        ).toBeInTheDocument();

        rerender(<PersonalityQuizPage initialArchetype="news-surfer" />);
        expect(screen.getByTestId('archetype-title')).toHaveTextContent('The Headline Surfer');
        expect(screen.getByTestId('personality-backdrop')).toHaveAttribute(
            'data-world',
            'personality-compass',
        );
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
        expect(buttons).toHaveLength(16);

        for (const button of buttons) {
            fireEvent.click(button);
            const cards = within(result).getAllByTestId('bot-recommendation-card');
            expect(cards).toHaveLength(1);
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

    it('keeps a finished quiz when the router coalesces rapid self-emitted searches', () => {
        const synced: Array<ArchetypeId | null> = [];
        const onSearch = (next: ArchetypeId | null) => {
            synced.push(next);
        };
        const { rerender } = render(<PersonalityQuizPage onArchetypeSearchChange={onSearch} />);
        answerAll();

        // Two rapid switcher clicks: a real router may only commit the second param.
        const switcher = screen.getByTestId('archetype-switcher');
        const [firstButton, secondButton] = within(switcher).getAllByRole('button');
        fireEvent.click(firstButton);
        fireEvent.click(secondButton);
        const committed = synced.at(-1) ?? undefined;
        expect(committed).toBeTruthy();

        rerender(
            <PersonalityQuizPage
                initialArchetype={committed ?? undefined}
                onArchetypeSearchChange={onSearch}
            />,
        );

        // The finished answers must survive the coalesced delivery.
        expect(screen.getByTestId('return-to-quiz-match')).toBeInTheDocument();
    });

    it('collects the optional Act-4 words and seeds the builder without changing the type', () => {
        const { rerender } = render(<PersonalityQuizPage />);

        // Walk to the last Act-3 question (index 11); Act 4 has not started yet.
        for (const [index, q] of PERSONALITY_QUESTIONS.entries()) {
            if (index === 11) break;
            fireEvent.click(screen.getByTestId(`quiz-option-${q.options[0].id}`));
            if ((index + 1) % 4 === 0) fireEvent.click(screen.getByTestId('continue-act'));
        }
        expect(
            within(screen.getByTestId('personality-quiz-card')).getByRole('heading', {
                level: 2,
                name: PERSONALITY_QUESTIONS[11].prompt,
            }),
        ).toBeInTheDocument();
        expect(screen.queryByTestId('quiz-self-description')).toBeNull();

        fireEvent.click(
            screen.getByTestId(`quiz-option-${PERSONALITY_QUESTIONS[11].options[0].id}`),
        );
        fireEvent.click(screen.getByTestId('continue-act'));
        const selfDesc = screen.getByTestId('quiz-self-description');
        const quizCard = screen.getByTestId('personality-quiz-card');
        expect(selfDesc).toBeInTheDocument();
        expect(
            quizCard.compareDocumentPosition(selfDesc) & Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();

        const words = 'no semiconductors, keep cash above 30 percent';
        for (const q of PERSONALITY_QUESTIONS.slice(12)) {
            fireEvent.change(screen.getByTestId('quiz-self-description'), {
                target: { value: words },
            });
            fireEvent.click(screen.getByTestId(`quiz-option-${q.options[0].id}`));
        }

        const result = screen.getByTestId('personality-result');
        expect(within(result).getByTestId('your-words')).toHaveTextContent(words);
        const buildLink = within(result).getByRole('link', { name: /build this bot/i });
        const idea =
            new URL(buildLink.getAttribute('href') ?? '', 'https://example.test').searchParams.get(
                'idea',
            ) ?? '';
        expect(idea).toContain(words);

        // A re-render (the router pushing the matched type back down) must not drop
        // the words. Only a full remount can, which is why the route never redirects.
        rerender(<PersonalityQuizPage initialAtmosphere="dusk" />);
        expect(
            within(screen.getByTestId('personality-result')).getByTestId('your-words'),
        ).toHaveTextContent(words);
    });

    it('offers to resume a draft saved on this device', () => {
        const firstThree = PERSONALITY_QUESTIONS.slice(0, 3);
        const draft = {
            answers: Object.fromEntries(firstThree.map((q) => [q.id, q.options[0].id])),
            stepIndex: 3,
            selfDescription: 'no crypto',
        };
        window.localStorage.setItem('benchify:personality-draft', JSON.stringify(draft));

        render(<PersonalityQuizPage />);

        const resumeBanner = screen.getByTestId('resume-quiz');
        const quizCard = screen.getByTestId('personality-quiz-card');
        expect(resumeBanner).toBeInTheDocument();
        expect(window.localStorage.getItem('benchify:personality-draft')).not.toBeNull();
        expect(
            quizCard.compareDocumentPosition(resumeBanner) & Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();
        fireEvent.click(screen.getByTestId('resume-quiz-button'));

        expect(screen.queryByTestId('resume-quiz')).toBeNull();
        expect(
            within(screen.getByTestId('personality-quiz-card')).getByRole('heading', {
                level: 2,
                name: PERSONALITY_QUESTIONS[3].prompt,
            }),
        ).toBeInTheDocument();
    });

    it('preserves quiz answers across inspection, returns on self-selection, and avoids self-navigation wipes', () => {
        const syncedParams: Array<string | null> = [];
        let routedParam: ArchetypeId | undefined;
        const onSearch = (next: ArchetypeId | null) => {
            syncedParams.push(next);
            routedParam = next ?? undefined;
        };
        const { rerender } = render(<PersonalityQuizPage onArchetypeSearchChange={onSearch} />);

        // Mirror the real router: every self-emitted search propagates back down as a prop.
        const propagate = () => {
            if (!routedParam) return;
            rerender(
                <PersonalityQuizPage
                    initialArchetype={routedParam}
                    onArchetypeSearchChange={onSearch}
                />,
            );
        };

        answerAll();
        propagate();

        const matchedSlug = syncedParams.at(-1);
        expect(matchedSlug).toBeTruthy();
        expect(screen.queryByTestId('return-to-quiz-match')).toBeNull();

        // Explore a different type without shifting the grid's cell count
        const switcher = screen.getByTestId('archetype-switcher');
        const gridButtons = within(switcher).getAllByRole('button');
        expect(gridButtons).toHaveLength(16);
        const matchCode = screen.getByTestId('archetype-code').textContent;
        const altButton = gridButtons.find((button) => button.textContent !== matchCode);
        expect(altButton).toBeDefined();
        if (altButton) fireEvent.click(altButton);
        propagate();

        expect(within(switcher).getAllByRole('button')).toHaveLength(16);
        expect(screen.getByTestId('archetype-code')).toHaveTextContent(
            altButton?.textContent ?? '',
        );
        expect(screen.getByTestId('return-to-quiz-match')).toBeInTheDocument();

        // Clicking your own cell returns to quiz_match mode
        const selfButton = gridButtons.find((button) => button.textContent === matchCode);
        expect(selfButton).toBeDefined();
        if (selfButton) fireEvent.click(selfButton);
        propagate();
        expect(screen.queryByTestId('return-to-quiz-match')).toBeNull();

        // Explore again and use explicit Back to my quiz match action
        if (altButton) fireEvent.click(altButton);
        propagate();
        fireEvent.click(screen.getByTestId('return-to-quiz-match'));
        propagate();
        expect(screen.getByTestId('archetype-code')).toHaveTextContent(matchCode ?? '');

        // External navigation to ?archetype=news-surfer then back to bare /personality resets to Q1
        rerender(
            <PersonalityQuizPage
                initialArchetype="news-surfer"
                onArchetypeSearchChange={onSearch}
            />,
        );
        expect(screen.getByTestId('archetype-title')).toHaveTextContent('The Headline Surfer');
        rerender(
            <PersonalityQuizPage initialArchetype={undefined} onArchetypeSearchChange={onSearch} />,
        );
        expect(screen.getByTestId('personality-quiz-card')).toBeInTheDocument();
    });
});
