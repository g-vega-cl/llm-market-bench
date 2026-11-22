import type { PersonalityAxis } from './personality-data';

export interface QuizOption {
    id: string;
    label: string;
    detail: string;
    deltas: Partial<Record<PersonalityAxis, number>>;
}

export interface QuizQuestion {
    id: string;
    prompt: string;
    context: string;
    options: [QuizOption, QuizOption, QuizOption, QuizOption];
}

export const PERSONALITY_QUESTIONS: QuizQuestion[] = [
    {
        id: 'q1-market-open',
        prompt: 'At 09:30 ET, semiconductor stocks gap down 4% on a sudden export tariff headline. What is your first instinct?',
        context: 'Opening Bell Shock · Framing',
        options: [
            {
                id: 'q1-a',
                label: 'Trace which domestic or supply-chain peers benefit right now',
                detail: 'Trade the policy shock immediately before the move finishes repricing.',
                deltas: { horizon: -12, signal: 14, contrarian: -10, cadence: 14 },
            },
            {
                id: 'q1-b',
                label: 'Check if the selloff is panic exhaustion without broken balance sheets',
                detail: 'Measure sentiment extremes and look to fade an overreaction.',
                deltas: { horizon: 2, signal: 4, contrarian: 16, cadence: 0 },
            },
            {
                id: 'q1-c',
                label: 'Audit your thesis and verify relative volume + price history before touching anything',
                detail: 'Run the structured checklist across portfolio holdings first.',
                deltas: { horizon: 6, signal: 0, contrarian: 2, cadence: -2 },
            },
            {
                id: 'q1-d',
                label: 'Ignore the tariff noise completely and review cash-flow screens tonight',
                detail: 'Headlines rarely change 12-month compounding power.',
                deltas: { horizon: 14, signal: -16, contrarian: 6, cadence: -14 },
            },
        ],
    },
    {
        id: 'q2-empty-tape',
        prompt: 'Three trading days pass and zero setups match your entry rules. How do you react?',
        context: 'Patience & Idle Cash',
        options: [
            {
                id: 'q2-a',
                label: 'Zero problem — staying in paper cash IS an active winning decision',
                detail: 'Wait as long as it takes for A+ quality and valuation margin.',
                deltas: { horizon: 14, signal: -10, contrarian: 4, cadence: -16 },
            },
            {
                id: 'q2-b',
                label: 'Scan breaking headlines to find where fresh catalysts are starting to move',
                detail: 'Idle cash feels like missed volatility during active sessions.',
                deltas: { horizon: -10, signal: 12, contrarian: -8, cadence: 16 },
            },
            {
                id: 'q2-c',
                label: 'Review open positions for thesis drift and check upcoming earnings calendars',
                detail: 'Stay patient between prints while pruning weakening theses.',
                deltas: { horizon: 4, signal: 4, contrarian: -2, cadence: 2 },
            },
            {
                id: 'q2-d',
                label: 'Hunt stretched sentiment pockets where fear or greed looks extreme',
                detail: 'Wait patiently for emotional mispricings to snap back.',
                deltas: { horizon: 2, signal: 2, contrarian: 14, cadence: -4 },
            },
        ],
    },
    {
        id: 'q3-earnings-beat',
        prompt: 'A company posts its fourth straight EPS beat and raises guidance, jumping +5% at the open. Your move?',
        context: 'Earnings Catalyst · Entry Timing',
        options: [
            {
                id: 'q3-a',
                label: 'Check RVOL > 1.5 and positive MACD to catch the multi-day post-print drift',
                detail: 'Structured event follow-through as long as it is not up >8% yet.',
                deltas: { horizon: -4, signal: 12, contrarian: -8, cadence: 10 },
            },
            {
                id: 'q3-b',
                label: 'Verify P/E and free cash flow first — never chase a pop near 52-week highs',
                detail: 'Valuation discipline beats post-earnings excitement.',
                deltas: { horizon: 14, signal: -14, contrarian: 6, cadence: -12 },
            },
            {
                id: 'q3-c',
                label: 'Skip buying today — if euphoria gets crowded over RSI 75, look to take profit',
                detail: 'Fade crowded consensus rather than joining it.',
                deltas: { horizon: 4, signal: 2, contrarian: 16, cadence: -2 },
            },
            {
                id: 'q3-d',
                label: 'Write down the exact mechanism connecting guidance to next-year margins first',
                detail: 'Verify price action vs VWAP and check past episodic memories.',
                deltas: { horizon: 8, signal: 2, contrarian: 0, cadence: 0 },
            },
        ],
    },
    {
        id: 'q4-drawdown',
        prompt: 'One of your highest-conviction positions drops 9% on zero company-specific news while the broad tape sells off.',
        context: 'Drawdown Management',
        options: [
            {
                id: 'q4-a',
                label: 'Check oversold RSI and add gradually once lower lows stop printing',
                detail: 'Step in against crowd fear when selling volume looks orderly.',
                deltas: { horizon: 4, signal: 2, contrarian: 16, cadence: 2 },
            },
            {
                id: 'q4-b',
                label: 'Run a fresh tool audit: is the original profit thesis intact or broken?',
                detail: 'Hold if intact, exit without ego if something structurally changed.',
                deltas: { horizon: 8, signal: 0, contrarian: 2, cadence: 2 },
            },
            {
                id: 'q4-c',
                label: 'Exit fast and redeploy into whichever sector holds relative strength today',
                detail: 'Preserve capital speed for stronger momentum waves.',
                deltas: { horizon: -12, signal: 10, contrarian: -12, cadence: 14 },
            },
            {
                id: 'q4-d',
                label: 'Hold serenely as long as free cash flow and long-term trend stay intact',
                detail: 'Daily drawdowns are irrelevant noise on quality balance sheets.',
                deltas: { horizon: 16, signal: -12, contrarian: 6, cadence: -14 },
            },
        ],
    },
    {
        id: 'q5-information-diet',
        prompt: 'If your bot could only keep ONE data stream inside its prompt window, which is non-negotiable?',
        context: 'Core Edge Source',
        options: [
            {
                id: 'q5-a',
                label: 'Breaking macro & sector news menu plus past market-event memories',
                detail: 'Narrative velocity drives rapid short-horizon repricing.',
                deltas: { horizon: -12, signal: 16, contrarian: -8, cadence: 12 },
            },
            {
                id: 'q5-b',
                label: 'Profitability multiples, free cash flow, and 52-week range health',
                detail: 'Hard company math protects downside better than headlines.',
                deltas: { horizon: 14, signal: -16, contrarian: 4, cadence: -12 },
            },
            {
                id: 'q5-c',
                label: 'Quarterly EPS surprise history + post-mortem earnings memories',
                detail: 'Historical event calibration beats guessing.',
                deltas: { horizon: -2, signal: 10, contrarian: -4, cadence: 8 },
            },
            {
                id: 'q5-d',
                label: 'The market-feeling sentiment barometer paired with oversold/VWAP spreads',
                detail: 'Gauge crowd psychology extremes before stepping in.',
                deltas: { horizon: 2, signal: 4, contrarian: 16, cadence: -2 },
            },
        ],
    },
    {
        id: 'q6-winning-trade',
        prompt: 'A stock you own spikes +14% in 48 hours and social sentiment turns euphoric. What do you do?',
        context: 'Exit Psychology',
        options: [
            {
                id: 'q6-a',
                label: 'Trim or exit right into euphoria before the narrative reverts',
                detail: 'Sell greed the same way you buy panic.',
                deltas: { horizon: -2, signal: 4, contrarian: 16, cadence: 6 },
            },
            {
                id: 'q6-b',
                label: 'Ride the breakout while VWAP & volume confirm institutional accumulation',
                detail: 'Winners keep winning when momentum just ignited.',
                deltas: { horizon: -8, signal: 10, contrarian: -14, cadence: 12 },
            },
            {
                id: 'q6-c',
                label: 'Re-check whether the valuation multiple is stretched past your fair ceiling',
                detail: 'Keep compounding unless fair value is clearly violated.',
                deltas: { horizon: 12, signal: -10, contrarian: 2, cadence: -10 },
            },
            {
                id: 'q6-d',
                label: 'Evaluate whether the original thesis is now fully realized; rotate if priced in',
                detail: 'Compare upside remaining against fresh catalysts.',
                deltas: { horizon: 6, signal: 2, contrarian: 4, cadence: 4 },
            },
        ],
    },
    {
        id: 'q7-sizing-style',
        prompt: 'How do you prefer a trading bot to deploy its paper portfolio slots?',
        context: 'Portfolio Construction',
        options: [
            {
                id: 'q7-a',
                label: 'Concentrated 4 x 25% core positions reviewed cleanly at every 3h slot',
                detail: 'Balanced accountability per position with clear thesis attribution.',
                deltas: { horizon: 8, signal: 0, contrarian: 0, cadence: -2 },
            },
            {
                id: 'q7-b',
                label: 'Fast tactical tickets rotating through active 30m/3h catalysts',
                detail: 'Keep capital cycling through whichever catalyst carries peak energy.',
                deltas: { horizon: -14, signal: 12, contrarian: -8, cadence: 16 },
            },
            {
                id: 'q7-c',
                label: 'Patient core baskets built slowly when rare valuation filters line up',
                detail: 'Low turnover, minimal fees, long compounding runway.',
                deltas: { horizon: 14, signal: -14, contrarian: 4, cadence: -16 },
            },
            {
                id: 'q7-d',
                label: 'Opportunistic mean-reversion tranches scaled around oversold flushes',
                detail: 'Dry powder reserved specifically for high-fear dislocations.',
                deltas: { horizon: 2, signal: 4, contrarian: 14, cadence: 0 },
            },
        ],
    },
    {
        id: 'q8-worst-feeling',
        prompt: 'Which trading mistake irritates you the MOST in hindsight?',
        context: 'Risk Regret Profile',
        options: [
            {
                id: 'q8-a',
                label: 'Chasing an already-exhausted hype headline right before it snaps back',
                detail: 'Being the last buyer in a crowded trade.',
                deltas: { horizon: 6, signal: -4, contrarian: 14, cadence: -6 },
            },
            {
                id: 'q8-b',
                label: 'Sitting frozen in cash while an obvious policy or sector trend doubles',
                detail: 'Missing explosive catalyst asymmetry through hesitation.',
                deltas: { horizon: -12, signal: 14, contrarian: -12, cadence: 14 },
            },
            {
                id: 'q8-c',
                label: 'Holding a broken narrative out of laziness because you stopped re-auditing',
                detail: 'Inertia instead of clear thesis discipline.',
                deltas: { horizon: 4, signal: 2, contrarian: 2, cadence: 4 },
            },
            {
                id: 'q8-d',
                label: 'Buying a glamorous story stock whose cash flow turned out to be negative',
                detail: 'Skipping fundamental quality checks for excitement.',
                deltas: { horizon: 14, signal: -14, contrarian: 4, cadence: -12 },
            },
        ],
    },
    {
        id: 'q9-clock-rhythm',
        prompt: 'When does your ideal bot earn its keep?',
        context: 'Timeframe & Market Clock',
        options: [
            {
                id: 'q9-a',
                label: 'Right around scheduled earnings releases, trading the clean 2-session drift',
                detail: 'Focused bursts around recurring quarterly reporting dates.',
                deltas: { horizon: -4, signal: 12, contrarian: -6, cadence: 10 },
            },
            {
                id: 'q9-b',
                label: 'Every active macro session where breaking news hits specific tickers',
                detail: 'High engagement with the live intraday news tape.',
                deltas: { horizon: -12, signal: 14, contrarian: -8, cadence: 16 },
            },
            {
                id: 'q9-c',
                label: 'Quietly week after week while quarterly compounders grind higher',
                detail: 'Set disciplined financial bars and let compounding work.',
                deltas: { horizon: 16, signal: -12, contrarian: 4, cadence: -14 },
            },
            {
                id: 'q9-d',
                label: 'During tense volatility flushes when the barometer flashes extreme fear',
                detail: 'Dormant in calm euphoria, decisive in red panic.',
                deltas: { horizon: 4, signal: 4, contrarian: 16, cadence: -2 },
            },
        ],
    },
    {
        id: 'q10-one-rule',
        prompt: 'Pick one iron rule to hard-code into the top of your bot prompt:',
        context: 'Prompt Constitution',
        options: [
            {
                id: 'q10-a',
                label: 'Never BUY unless you can state the profit mechanism in one crisp sentence',
                detail: 'Full tool-first synthesis connecting catalyst, price, and thesis.',
                deltas: { horizon: 8, signal: 0, contrarian: 2, cadence: 0 },
            },
            {
                id: 'q10-b',
                label: 'Trade the post-earnings drift, never the blind headline spike above +8%',
                detail: 'Confirm EPS surprise streaks + volume expansion before entering.',
                deltas: { horizon: -2, signal: 10, contrarian: -6, cadence: 8 },
            },
            {
                id: 'q10-c',
                label: 'Only touch cash-generative companies at reasonable P/E; HOLD without guilt',
                detail: 'Quality multiples + trend alignment above everything else.',
                deltas: { horizon: 14, signal: -14, contrarian: 4, cadence: -14 },
            },
            {
                id: 'q10-d',
                label: 'Fade crowd exhaustion: buy orderly oversold flushes, exit into euphoria',
                detail: 'Keep dry powder for emotional market overreactions.',
                deltas: { horizon: 2, signal: 4, contrarian: 16, cadence: 0 },
            },
        ],
    },
];
