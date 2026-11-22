/**
 * The four behavioural axes the diagnostic scores, and nothing else.
 *
 * Kept separate from the type grid and the archetype catalogue so both can
 * import the axis vocabulary without a cycle.
 */
export const PERSONALITY_AXES = ['horizon', 'signal', 'contrarian', 'cadence'] as const;

export type PersonalityAxis = (typeof PERSONALITY_AXES)[number];

export type AxisProfile = Record<PersonalityAxis, number>;

export interface AxisDefinition {
    id: PersonalityAxis;
    label: string;
    lowLabel: string;
    highLabel: string;
}

export const AXIS_DEFINITIONS: AxisDefinition[] = [
    {
        id: 'horizon',
        label: 'Patience & Horizon',
        lowLabel: 'Session Swings',
        highLabel: 'Multi-Quarter Thesis',
    },
    {
        id: 'signal',
        label: 'Signal Anchor',
        lowLabel: 'Balance Sheet & Value',
        highLabel: 'Live Headlines & Catalysts',
    },
    {
        id: 'contrarian',
        label: 'Crowd Stance',
        lowLabel: 'Ride Trend Confirmation',
        highLabel: 'Fade Panic & Euphoria',
    },
    {
        id: 'cadence',
        label: 'Execution Tempo',
        lowLabel: 'Selective Patience',
        highLabel: 'Active Rotation',
    },
];
