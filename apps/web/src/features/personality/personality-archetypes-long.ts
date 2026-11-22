import type { InvestingArchetype } from './personality-archetypes';

/**
 * The eight `L…` cells (long horizon). Split from the `Q…` cells so neither
 * catalogue file crosses the 400-LOC ceiling.
 */
export const LONG_ARCHETYPES: InvestingArchetype[] = [
    {
        id: 'value-compounder',
        code: 'LVFP',
        title: 'The Patient Compounder',
        tagline:
            'Ignores noisy headlines in favor of cash flow, valuation discipline, and clean trends.',
        summary:
            'You treat every trade like owning a durable business. Noise gets tuned out; missed hype bothers you less than overpaying, so you wait for clear value.',
        strengths: [
            'Resists FOMO during speculative headline spikes',
            'Anchors decisions to free cash flow and multiples',
            'Stays calm holding winners across slow pullbacks',
        ],
        watchout: 'May hesitate to cut or rotate quickly when a macro regime genuinely flips.',
        recipeName: 'Quality Value Screener',
        builderIdeaPrompt:
            'Build a quality value bot that ignores news headlines, screens for P/E under 28, positive free cash flow, positive MACD, and price below 90% of its 52-week high, holding cash when nothing clears every rule.',
        idealProfile: { horizon: 88, signal: 12, contrarian: 88, cadence: 12 },
    },
    {
        id: 'value-rotator',
        code: 'LVFR',
        title: 'The Value Rotator',
        tagline:
            'Rotates into cash-rich value names whenever price slips below VWAP and RSI cools.',
        summary:
            'You hold a thesis for quarters yet still rotate the book the moment a name gets cheap enough to matter. Price falling under VWAP while RSI cools is your entry cue, and you refuse to let headlines talk you into or out of the position.',
        strengths: [
            'Buys cash-generative names once RSI falls under 40',
            'Adds on weakness below VWAP instead of chasing strength',
            'Rotates stale slots into cheaper free cash flow regularly',
        ],
        watchout:
            'Rotating into every dip can mean averaging down on a name whose free cash flow is quietly deteriorating.',
        recipeName: 'Value Pullback Rotator',
        builderIdeaPrompt:
            'Build a value rotation bot that enters only when RSI is below 40, price sits under VWAP, and free cash flow is positive, keeping 168 hours of memories so it does not re-buy a name it just sold, ignoring news feeds entirely, and holding cash whenever no candidate clears all three filters.',
        idealProfile: { horizon: 88, signal: 12, contrarian: 88, cadence: 88 },
    },
    {
        id: 'compound-buyer',
        code: 'LVMP',
        title: 'The Compounder Buyer',
        tagline:
            'Accumulates cheap high-return businesses, but only while the trend still confirms.',
        summary:
            'You buy businesses that earn well on their equity and still trade at a sane multiple, then hold them for years. Momentum only times your entry: once MACD rolls over you wait rather than average down into a falling price.',
        strengths: [
            'Buys P/E under 22 only with return on equity above 12',
            'Waits for positive MACD before committing new capital',
            'Holds the same position for quarters instead of trading noise',
        ],
        watchout:
            'A cheap multiple on a high-ROE business is still a value trap when the growth behind that return is fading.',
        recipeName: 'Patient Compound Accumulator',
        builderIdeaPrompt:
            'Build a patient accumulation bot that screens for P/E under 22 and ROE above 12, confirms MACD is positive before buying, stores 168 hours of memories to avoid re-entering names it already owns, skips news entirely, and sits in cash when no business passes all three filters.',
        idealProfile: { horizon: 88, signal: 12, contrarian: 12, cadence: 12 },
    },
    {
        id: 'quality-rotator',
        code: 'LVMR',
        title: 'The Quality Rotator',
        tagline: 'Rotates the book toward profitable leaders already trading near their highs.',
        summary:
            'You accept that quality shows up in the price: strong return on equity plus a stock in the upper half of its yearly range. Volume above its own average tells you the move has real participation, so you rotate the sleeve and keep it turning.',
        strengths: [
            'Rotates into names with ROE above 10 and 52-week percentile over 60',
            'Requires RVOL above 1.1 before adding any exposure',
            'Trims laggards weekly to keep capital in the leaders',
        ],
        watchout:
            'Chasing 52-week leaders on merely average volume hands you the top of a move that is already distributing.',
        recipeName: 'Quality Momentum Rotator',
        builderIdeaPrompt:
            'Build a quality momentum rotator that buys only when ROE exceeds 10, price sits above the 60th percentile of its 52-week range, and RVOL clears 1.1, keeping 168 hours of memories so it will not re-buy the same name, with no news input and a cash sleeve whenever the screen comes up empty.',
        idealProfile: { horizon: 88, signal: 12, contrarian: 12, cadence: 88 },
    },
    {
        id: 'contrarian-diver',
        code: 'LNFP',
        title: 'The Contrarian Diver',
        tagline:
            'Buys orderly liquidation panic when sentiment overshoots and sells into crowd euphoria.',
        summary:
            'When the tape panics on recycled headlines, you read sentiment extremes and volume structure — buying exhaustion below VWAP instead of herd consensus.',
        strengths: [
            'Comfortable buying quality names during sudden flushes',
            'Separates structural balance-sheet breaks from panic',
            'Takes profits cleanly into euphoric consensus peaks',
        ],
        watchout:
            'Requires hard discipline against catching falling knives when fundamentals actually break.',
        recipeName: 'Contrarian Sentiment Fader',
        builderIdeaPrompt:
            'Build a contrarian mean-reversion bot that checks the market-feeling barometer, looks for oversold RSI below 35 and price below VWAP on orderly volume with no broken fundamentals, and exits profitable positions into euphoria.',
        idealProfile: { horizon: 88, signal: 88, contrarian: 88, cadence: 12 },
    },
    {
        id: 'systems-architect',
        code: 'LNFR',
        title: 'The Thesis Auditor',
        tagline:
            'Re-audits every open thesis each cycle, blending catalysts, valuation, and memory checks.',
        summary:
            'You value intellectual honesty over any single signal. Every open thesis is re-audited against quotes, price history, news chains, and past post-mortems — and rotated the moment it stops paying for its slot.',
        strengths: [
            'Forces explicit profit logic before risking capital',
            'Audits existing holdings continuously for broken rules',
            'Blends macro news, valuation, and technical structure',
        ],
        watchout:
            'Constant re-auditing can rotate a working position out before its thesis has time to resolve.',
        recipeName: 'Claude Agent Portfolio Mirror',
        builderIdeaPrompt:
            'Build a balanced portfolio mirror bot with 4x25% long sizing that traces catalyst-to-earnings chains, audits open positions every slot to exit broken theses, and requires RSI below 75, positive VWAP spread, and RVOL above 1.2.',
        idealProfile: { horizon: 88, signal: 88, contrarian: 88, cadence: 88 },
    },
    {
        id: 'catalyst-holder',
        code: 'LNMP',
        title: 'The Catalyst Holder',
        tagline: 'Holds profitable leaders through a named catalyst, entering only with the trend.',
        summary:
            'You wait for a named catalyst to lift a business that already earns well, then hold that position for quarters instead of days. The news window explains why capital is arriving; MACD and a high 52-week percentile confirm the trend agrees with the story.',
        strengths: [
            'Buys ROE above 12 only after a catalyst clears the 72h news window',
            'Requires positive MACD and price above the 75th percentile',
            'Holds the position for quarters instead of scalping the print',
        ],
        watchout:
            'Holding a catalyst name for quarters means one guidance cut can erase the whole move before you get a chance to react.',
        recipeName: 'Catalyst Hold Sleeve',
        builderIdeaPrompt:
            'Build a catalyst hold sleeve that reads 72 hours of news for a named event, then buys only if MACD is positive, price sits above the 75th percentile of its 52-week range, and ROE exceeds 12, keeping 168 hours of memories and holding cash until one catalyst clears every filter.',
        idealProfile: { horizon: 88, signal: 88, contrarian: 12, cadence: 12 },
    },
    {
        id: 'catalyst-quant',
        code: 'LNMR',
        title: 'The Catalyst Quant',
        tagline:
            'Finds multi-quarter EPS surprise streaks and trades the clean post-print drift window.',
        summary:
            'You trust measurable repeatability over vibes: EPS beats backed by guidance raises, RVOL above 1.5x, and positive MACD while skipping extended spikes.',
        strengths: [
            'Combines surprise history with technical confirmation',
            'Avoids noisy churn outside verified event windows',
            'Follows pre-committed exit rules when drift stalls',
        ],
        watchout: 'Stay mindful of correlated sector exposure during peak earnings weeks.',
        recipeName: 'Earnings Catalyst Hunter',
        builderIdeaPrompt:
            'Build an earnings catalyst drift bot checking 4 quarters of EPS surprise history and management guidance over 72h earnings news, filtering for RVOL above 1.5 and positive MACD while skipping names already up over 8%.',
        idealProfile: { horizon: 88, signal: 88, contrarian: 12, cadence: 88 },
    },
];
