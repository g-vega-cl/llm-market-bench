import type { PositionWithReasoning } from '@llm-market-bench/database';
import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import type { FrontierTheme } from '../api/fetch-portfolios';

interface FrontierThemeCardsProps {
    themes: FrontierTheme[];
    positions: PositionWithReasoning[];
}

export function FrontierThemeCards({ themes, positions }: FrontierThemeCardsProps) {
    if (!themes || themes.length === 0) return null;

    // Total invested cash in the portfolio
    const totalInvestedCash = positions.reduce(
        (sum, pos) => sum + (pos.quantity ?? 0) * (pos.average_cost_basis ?? 0),
        0,
    );

    return (
        <section className="space-y-4">
            <div className="flex items-center justify-between">
                <SectionHeading gradient="electric">Active Frontier Themes</SectionHeading>
                <Badge variant="soft" size="sm" colorScheme="accent">
                    5-Point Supercycle Rubric
                </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {themes.map((theme) => {
                    const themeTickers = new Set(
                        (Array.isArray(theme.tickers) ? theme.tickers : []).map((t) =>
                            String(t).toUpperCase(),
                        ),
                    );

                    // Compute theme aggregate stats
                    const themePositions = positions.filter(
                        (p) => p.ticker && themeTickers.has(p.ticker.toUpperCase()),
                    );

                    const themeInvested = themePositions.reduce(
                        (sum, p) => sum + (p.quantity ?? 0) * (p.average_cost_basis ?? 0),
                        0,
                    );
                    const themePnlUsd = themePositions.reduce(
                        (sum, p) => sum + (p.unrealized_pnl_usd ?? 0),
                        0,
                    );
                    const themeWeightPct =
                        totalInvestedCash > 0 ? (themeInvested / totalInvestedCash) * 100 : 0;
                    const themePnlPct = themeInvested > 0 ? (themePnlUsd / themeInvested) * 100 : 0;

                    return (
                        <Card
                            key={theme.theme_name}
                            variant="outlined"
                            padding="md"
                            className="bg-zinc-900/40 border-zinc-800 flex flex-col justify-between hover:border-zinc-700 transition-colors"
                        >
                            <div className="space-y-3">
                                <div className="flex items-start justify-between gap-2">
                                    <h4 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                                        <span>⚛️</span>
                                        <span>{theme.theme_name}</span>
                                    </h4>
                                    <Badge variant="soft" size="sm" colorScheme="info">
                                        Rubric {theme.rubric_score}/5
                                    </Badge>
                                </div>

                                <p className="text-xs text-zinc-400 line-clamp-3 leading-relaxed">
                                    {theme.thesis}
                                </p>

                                <div className="text-xs text-zinc-500 bg-zinc-950/50 p-2.5 rounded border border-zinc-800/60">
                                    <span className="font-semibold text-zinc-400">Catalysts: </span>
                                    {theme.catalysts}
                                </div>
                            </div>

                            <div className="mt-4 pt-3 border-t border-zinc-800/80 flex items-center justify-between text-xs">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="text-zinc-500">Pure Plays:</span>
                                    {Array.isArray(theme.tickers) &&
                                        theme.tickers.map((t) => (
                                            <span
                                                key={t}
                                                className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-200 font-mono font-medium"
                                            >
                                                {t}
                                            </span>
                                        ))}
                                </div>

                                {themePositions.length > 0 && (
                                    <div className="flex items-center gap-3">
                                        <span className="text-zinc-400">
                                            Weight:{' '}
                                            <strong className="text-zinc-200">
                                                {themeWeightPct.toFixed(1)}%
                                            </strong>
                                        </span>
                                        <span
                                            className={`font-semibold ${
                                                themePnlPct >= 0
                                                    ? 'text-emerald-400'
                                                    : 'text-rose-400'
                                            }`}
                                        >
                                            {themePnlPct >= 0 ? '+' : ''}
                                            {themePnlPct.toFixed(1)}%
                                        </span>
                                    </div>
                                )}
                            </div>
                        </Card>
                    );
                })}
            </div>
        </section>
    );
}
