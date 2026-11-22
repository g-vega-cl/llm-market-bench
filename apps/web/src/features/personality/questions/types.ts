import type { PersonalityAxis } from '../personality-axes';

export interface QuizOption {
    id: string;
    label: string;
    detail: string;
    deltas: Partial<Record<PersonalityAxis, number>>;
}

export interface QuizQuestion {
    id: string;
    /** The axis this question primarily probes (~70% of its delta mass). */
    act: PersonalityAxis;
    prompt: string;
    context: string;
    options: [QuizOption, QuizOption, QuizOption, QuizOption];
}

export interface QuizActDefinition {
    axis: PersonalityAxis;
    title: string;
    blurb: string;
}
