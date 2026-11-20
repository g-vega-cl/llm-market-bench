/** Tickers that must stay uppercase when a portfolio id is turned into a label. */
const ACRONYMS = new Set([
    'spy',
    'tlt',
    'qqq',
    'vix',
    'etf',
    'ai',
    'gpt',
    'llm',
    'dca',
    'ipo',
    'cpi',
    'fed',
    'sma',
    'usd',
]);

/** `sys-max-pain` -> `Max Pain`, `sys-daily-spy-demo-model` -> `Daily SPY Demo Model`. */
export function portfolioLabel(ownerId: string): string {
    // `~typesafe/jev-latest` names an operator and a deployment, not a strategy:
    // drop the namespaced segment and the `-latest` marker, keep the rest.
    const cleaned = ownerId
        .replace(/^sys-/, '')
        .replace(/~[^/]+\//g, '')
        .replace(/-latest$/i, '');
    const words = cleaned
        .split(/[-_/]+/)
        .map((word) => word.replace(/^~/, ''))
        .filter(Boolean);

    return words
        .map((word) =>
            ACRONYMS.has(word.toLowerCase())
                ? word.toUpperCase()
                : word.charAt(0).toUpperCase() + word.slice(1),
        )
        .join(' ');
}
