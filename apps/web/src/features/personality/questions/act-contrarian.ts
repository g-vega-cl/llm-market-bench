import type { QuizQuestion } from './types';

/**
 * Act 3 — Crowd Stance. Target deltas +-14/+-5 on `contrarian`, cross-loadings
 * <= 4, symmetric about zero, half the questions presented high pole first.
 */
export const CONTRARIAN_QUESTIONS: QuizQuestion[] = [
    {
        id: 'a3-euphoric-winner',
        act: 'contrarian',
        prompt: 'A holding spikes +14% in 48 hours and sentiment turns euphoric.',
        context: 'Euphoric Winner',
        options: [
            {
                id: 'a3-euphoric-a',
                label: 'Ride it while VWAP and volume confirm accumulation',
                detail: 'Strength confirms strength; do not interrupt a compounder.',
                deltas: { contrarian: -14, signal: -2, horizon: 2, cadence: 4 },
            },
            {
                id: 'a3-euphoric-b',
                label: 'Trail a stop and let the trend pick the exit',
                detail: 'Stay in until the market says otherwise.',
                deltas: { contrarian: -5, horizon: 1, cadence: 2 },
            },
            {
                id: 'a3-euphoric-c',
                label: 'Trim into the strength and keep a core position',
                detail: 'Bank some of the crowd’s enthusiasm, keep the thesis.',
                deltas: { contrarian: 5, horizon: -1, cadence: -2 },
            },
            {
                id: 'a3-euphoric-d',
                label: 'Exit fully — euphoric consensus is the sell signal',
                detail: 'When everyone agrees, the information is already priced.',
                deltas: { contrarian: 14, signal: 2, horizon: -2, cadence: -4 },
            },
        ],
    },
    {
        id: 'a3-panic-flush',
        act: 'contrarian',
        prompt: 'The market barometer flashes extreme fear and quality names are flushing.',
        context: 'Panic Flush',
        options: [
            {
                id: 'a3-panic-a',
                label: 'Back the truck up — panic is the only real discount',
                detail: 'Dislocation is the product; buy it in size.',
                deltas: { contrarian: 14, horizon: 4, cadence: 2 },
            },
            {
                id: 'a3-panic-b',
                label: 'Start scaling into oversold names with intact cash flow',
                detail: 'Buy in tranches while the selling is orderly.',
                deltas: { contrarian: 5, horizon: 2 },
            },
            {
                id: 'a3-panic-c',
                label: 'Wait for the first higher low, then follow it',
                detail: 'Confirmation is cheaper than being right early.',
                deltas: { contrarian: -5, horizon: -2 },
            },
            {
                id: 'a3-panic-d',
                label: 'Buy strength instead — the first names out of the flush',
                detail: 'Rotate to what the market is already rewarding.',
                deltas: { contrarian: -14, horizon: -4, cadence: -2 },
            },
        ],
    },
    {
        id: 'a3-crowded-narrative',
        act: 'contrarian',
        prompt: 'A sector is +30% in six weeks on a narrative everybody repeats.',
        context: 'Crowded Narrative',
        options: [
            {
                id: 'a3-crowded-a',
                label: 'Join it while relative strength keeps leading',
                detail: 'Crowds are right for longer than contrarians admit.',
                deltas: { contrarian: -14, signal: -4, cadence: 2 },
            },
            {
                id: 'a3-crowded-b',
                label: 'Only enter on a pullback that holds the trend',
                detail: 'Better price inside a trend that is still working.',
                deltas: { contrarian: -5, signal: -2 },
            },
            {
                id: 'a3-crowded-c',
                label: 'Rotate to the laggards nobody has repriced yet',
                detail: 'Second-order names are where the remaining asymmetry lives.',
                deltas: { contrarian: 5, signal: 2 },
            },
            {
                id: 'a3-crowded-d',
                label: 'Stay out — nothing here is worth owning at this price',
                detail: 'No position is a valid position.',
                deltas: { contrarian: 14, signal: 4, cadence: -2 },
            },
        ],
    },
    {
        id: 'a3-stop-rule',
        act: 'contrarian',
        prompt: 'A winner reverses 8%. What is the stop rule?',
        context: 'Stop Rule',
        options: [
            {
                id: 'a3-stop-a',
                label: 'Exit on the reversal — the crowd just turned',
                detail: 'Treat the turn as information, not noise.',
                deltas: { contrarian: 14, horizon: 2, cadence: -2 },
            },
            {
                id: 'a3-stop-b',
                label: 'Cut half and re-underwrite the thesis',
                detail: 'Reduce exposure while you think.',
                deltas: { contrarian: 5, horizon: 1, cadence: -1 },
            },
            {
                id: 'a3-stop-c',
                label: 'Trail the 8% and re-enter if strength resumes',
                detail: 'Keep the name on the bench, not in the book.',
                deltas: { contrarian: -5, horizon: -1, cadence: 1 },
            },
            {
                id: 'a3-stop-d',
                label: 'No price stop — only a trend break decides',
                detail: 'Fixed stops sell into noise; structure is the signal.',
                deltas: { contrarian: -14, horizon: -2, cadence: 2 },
            },
        ],
    },
];
