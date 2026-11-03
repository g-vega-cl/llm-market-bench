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
        <section className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <SectionHeading gradient="electric">Active Frontier Themes</SectionHeading>
                <Badge variant="soft" size="sm" colorScheme="accent" radius="none">
                    5-Point Supercycle Rubric
                </Badge>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4 items-stretch">
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
                            className="h-full flex flex-col justify-between rounded-none hover:border-boxel-bevel-hi transition-colors gap-4"
                        >
                            <div className="flex flex-col gap-3">
                                <div className="flex items-start justify-between gap-2">
                                    <h4 className="text-sm font-bold text-boxel-ink flex items-center gap-2">
                                        <span>⚛️</span>
                                        <span>{theme.theme_name}</span>
                                    </h4>
                                    <Badge
                                        variant="soft"
                                        size="sm"
                                        colorScheme="info"
                                        radius="none"
                                    >
                                        Rubric {theme.rubric_score}/5
                                    </Badge>
                                </div>

                                <p className="text-xs font-normal text-zinc-400 line-clamp-3 leading-relaxed">
                                    {theme.thesis}
                                </p>

                                <div className="text-xs font-normal text-zinc-500 bg-zinc-950/50 p-2.5 rounded-none border border-zinc-800/60">
                                    <span className="font-bold text-zinc-400">Catalysts: </span>
                                    {theme.catalysts}
                                </div>
                            </div>

                            <div className="pt-3 border-t border-zinc-800/80 flex items-center justify-between text-xs">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="text-zinc-500">Pure Plays:</span>
                                    {Array.isArray(theme.tickers) &&
                                        theme.tickers.map((t) => (
                                            <span
                                                key={t}
                                                className="px-1.5 py-0.5 rounded-none bg-zinc-800 text-zinc-200 font-mono text-xs font-bold"
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
                                            className={`font-bold font-mono ${
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
