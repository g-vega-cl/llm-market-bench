import type { InvestingArchetype } from './personality-archetypes';

/**
 * The eight `Q…` cells (quick horizon). Split from the `L…` cells so neither
 * catalogue file crosses the 400-LOC ceiling.
 */
export const QUICK_ARCHETYPES: InvestingArchetype[] = [
    {
        id: 'bargain-snapper',
        code: 'QVFP',
        title: 'The Bargain Snapper',
        tagline:
            'Snaps up beaten-down cheap names at maximum pessimism, then waits for the bounce.',
        summary:
            'You want the deepest discount on the board: a low multiple, a stock pinned to the floor of its 52-week band, and momentum fully washed out. You take one shot per name and let the snapback do the work rather than trading around the position.',
        strengths: [
            'Buys RSI under 30 with price in the bottom 30% of its range',
            'Demands P/E under 20 before touching a washed-out chart',
            'Holds a single entry instead of adding into more weakness',
        ],
        watchout:
            'Buying every washed-out chart at once guarantees you eventually own a business whose cheapness was earned by real decline.',
        recipeName: 'Deep Value Snapback',
        builderIdeaPrompt:
            'Build a deep value snapback bot that fires only when RSI is below 30, price is under the 30th percentile of its 52-week range, and P/E is below 20, with no news feed and no memory of prior trades, taking one position per name and staying in cash the rest of the time.',
        idealProfile: { horizon: 12, signal: 12, contrarian: 88, cadence: 12 },
    },
    {
        id: 'deep-value-trader',
        code: 'QVFR',
        title: 'The Deep-Value Trader',
        tagline:
            'Trades cheap cash-generative names below VWAP, cycling the book instead of holding.',
        summary:
            'You treat value as a short-horizon trade rather than a holding period. Any name under 25 times earnings with positive free cash flow qualifies once RSI cools below 45 and price slips under VWAP, and you recycle that capital as soon as the discount closes.',
        strengths: [
            'Screens for P/E under 25 paired with positive free cash flow',
            'Enters only while price is trading below VWAP',
            'Recycles capital weekly rather than holding through chop',
        ],
        watchout:
            'Trading the same cheap names in and out bleeds spread and fees faster than the value edge can compound.',
        recipeName: 'Cheap Tape Rotator',
        builderIdeaPrompt:
            'Build a cheap tape rotator that enters when RSI is under 45, price is below VWAP, free cash flow is positive, and P/E stays under 25, runs with no news input and no trade memory, and holds cash between rotations rather than forcing a position every session.',
        idealProfile: { horizon: 12, signal: 12, contrarian: 88, cadence: 88 },
    },
    {
        id: 'value-scalper',
        code: 'QVMP',
        title: 'The Value Scalper',
        tagline: 'Scalps brief momentum bursts inside reasonably priced, profitable companies.',
        summary:
            'You stay in cheap-enough, profitable companies but only for the length of one momentum burst. MACD turning positive is the trigger, a reasonable multiple and positive return on equity are the permission slip, and you are flat again within days.',
        strengths: [
            'Buys only when MACD turns positive on a name with P/E under 35',
            'Filters for ROE above 8 before taking any scalp',
            'Flattens the position within days instead of holding it',
        ],
        watchout:
            'Scalping small momentum bursts in unremarkable names often costs more in spread than the move was ever worth.',
        recipeName: 'Fundamental Momentum Scalper',
        builderIdeaPrompt:
            'Build a fundamental momentum scalper that buys when P/E is under 35, ROE is above 8, and MACD has just turned positive, takes no news input and keeps no memory between sessions, then exits on the first MACD rollover and holds cash until a new trigger appears.',
        idealProfile: { horizon: 12, signal: 12, contrarian: 12, cadence: 12 },
    },
    {
        id: 'multiple-rotator',
        code: 'QVMR',
        title: 'The Multiple Rotator',
        tagline: 'Rotates quickly into cheap names being re-rated on heavy, above-average volume.',
        summary:
            'You hunt a re-rating while it is still in progress: a multiple under 40, price already through the 60th percentile of its 52-week band, and volume running 1.3 times normal. You stay only while that participation holds, then move the capital to the next candidate.',
        strengths: [
            'Buys P/E under 40 only once RVOL exceeds 1.3',
            'Requires price above the 60th percentile of its 52-week range',
            'Rotates out as soon as volume participation fades',
        ],
        watchout:
            'Re-rating trades reverse hard, and a 48-hour memory is short enough to let you re-enter the same fading name twice.',
        recipeName: 'Multiple Re-Rating Rotator',
        builderIdeaPrompt:
            'Build a multiple re-rating rotator that enters when P/E is under 40, MACD is positive, RVOL is above 1.3, and price clears the 60th percentile of its 52-week range, keeping 48 hours of memories to block repeat entries, ignoring news, and parking in cash when volume dries up.',
        idealProfile: { horizon: 12, signal: 12, contrarian: 12, cadence: 88 },
    },
    {
        id: 'headline-fader',
        code: 'QNFP',
        title: 'The Headline Fader',
        tagline: 'Fades panic headlines by buying washed-out names trading below VWAP.',
        summary:
            'You read the 24-hour news tape looking for fear that has run past the facts. When a headline pushes RSI below 30 while the stock trades under VWAP and near its yearly low, you buy the overreaction and wait for the tape to normalise.',
        strengths: [
            'Buys after a panic headline pushes RSI under 30',
            'Enters below VWAP only when price is under the 35th percentile',
            'Uses a 48h memory to avoid re-buying the same panic story',
        ],
        watchout:
            'Some headlines are the first report of a real problem, and fading them means buying the start of a long decline.',
        recipeName: 'Headline Panic Fader',
        builderIdeaPrompt:
            'Build a headline panic fader that scans 24 hours of news, then buys only when RSI is under 30, price is below VWAP, and the stock sits under the 35th percentile of its 52-week range, carrying 48 hours of memories to skip repeat entries and holding cash when no panic qualifies.',
        idealProfile: { horizon: 12, signal: 88, contrarian: 88, cadence: 12 },
    },
    {
        id: 'news-contrarian',
        code: 'QNFR',
        title: 'The News Contrarian',
        tagline: 'Trades against fresh news on cash-rich names, rotating the book every session.',
        summary:
            'You treat the 24-hour news window as a sentiment gauge and take the other side when it overshoots. A cash-generative business showing RSI under 40 and price below VWAP is your setup, and you rotate out as soon as the crowd catches up to the reversal.',
        strengths: [
            'Fades 24h news spikes in names with positive free cash flow',
            'Buys RSI under 40 while price trades below VWAP',
            'Rotates out on the bounce instead of holding the reversal',
        ],
        watchout:
            'Rotating daily against the news churns the account while a genuine trend keeps running without you in it.',
        recipeName: 'Fast News Contrarian',
        builderIdeaPrompt:
            'Build a fast news contrarian bot that reads 24 hours of headlines, buys when RSI is under 40, price is below VWAP, and free cash flow is positive, keeps 96 hours of memories so it does not fade the same story twice, and returns to cash once the reversal plays out.',
        idealProfile: { horizon: 12, signal: 88, contrarian: 88, cadence: 88 },
    },
    {
        id: 'print-trader',
        code: 'QNMP',
        title: 'The Print Trader',
        tagline:
            'Trades the print window, catching volume spikes in leaders that confirm the trend.',
        summary:
            'You trade a narrow window around a scheduled print, when volume and news land together. Only a leader trading above the top fifth of its 52-week band with MACD positive qualifies, and you are back in cash before the drift becomes crowded.',
        strengths: [
            'Enters only when RVOL exceeds 2 inside the 24h news window',
            'Requires price above the 80th percentile and positive MACD',
            'Exits after the print window instead of holding the drift',
        ],
        watchout:
            'Waiting for volume above twice normal often means the easy part of the print move is already gone by the time you fill.',
        recipeName: 'Print Window Scalper',
        builderIdeaPrompt:
            'Build a print window scalper that watches 24 hours of earnings news, enters only when RVOL is above 2, MACD is positive, and price is above the 80th percentile of its 52-week range, keeps 72 hours of memories to avoid re-trading one print, and exits to cash when the window closes.',
        idealProfile: { horizon: 12, signal: 88, contrarian: 12, cadence: 12 },
    },
    {
        id: 'news-surfer',
        code: 'QNMR',
        title: 'The Headline Surfer',
        tagline:
            'Reads policy shocks and sector catalysts first, riding fresh narrative repricing early.',
        summary:
            'You track where capital must reprice right now — tariffs, chips, launches — pairing headline velocity with guardrails so you never chase exhausted highs.',
        strengths: [
            'Spreads risk across liquid high-velocity themes fast',
            'Maps macro news directly to second-order equity movers',
            'Cuts stale narratives promptly instead of bag-holding',
        ],
        watchout:
            'Avoid chasing extended RSI extremes once everybody already agrees on the headline.',
        recipeName: 'Trump & Chips News Momentum',
        builderIdeaPrompt:
            'Build a news momentum bot scanning 48h chip and policy headlines paired with tariff memories, verifying P/E under 45 and RSI under 70 before entering.',
        idealProfile: { horizon: 12, signal: 88, contrarian: 12, cadence: 88 },
    },
];
