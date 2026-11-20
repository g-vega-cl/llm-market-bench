import {
    Badge,
    Button,
    Card,
    EmptyState,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import type { PublicBoardCard, PublicDesk } from '~/features/recipes/api/public-board-api';
import { STARTER_RECIPES } from '~/features/recipes/starter-templates';
import type {
    EquityPoint,
    LeaderboardRow,
    PortfolioLeaderboard,
} from '../api/portfolio-leaderboard';
import { EquityChart } from './EquityChart';
import { formatPct } from './format-pct';
import { HomeHero } from './HomeHero';
import { modelLabel } from './model-label';
import { TopPortfolios } from './TopPortfolios';

export interface RecipeDeskHomePageProps {
    desk: PublicDesk;
    leaderboard?: PortfolioLeaderboard;
    onFork: (recipeId: string) => void;
    forkingId?: string | null;
    error?: string | null;
}

function returnTone(value: number | null): 'success' | 'danger' | 'muted' {
    if (value === null) return 'muted';
    return value >= 0 ? 'success' : 'danger';
}

function RecipeCard({
    card,
    onFork,
    isForking,
}: {
    card: PublicBoardCard;
    onFork: (recipeId: string) => void;
    isForking: boolean;
}) {
    const tone = returnTone(card.returnPct);
    return (
        <Card padding="md" className="h-full min-w-0 flex flex-col gap-3">
            <div className="flex flex-wrap items-start justify-between gap-2 pb-2 border-b-2 border-voxel-bevel-hi">
                <div className="flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-voxel-ink break-words">
                        {card.name}
                    </span>
                    <span className="text-xs font-normal text-voxel-muted">
                        {card.lastAction
                            ? `${card.lastAction.action} ${card.lastAction.ticker}`
                            : 'No fills yet'}
                        {card.runsToday > 0 ? ` · ${card.runsToday} runs today` : ''}
                    </span>
                </div>
                <Badge colorScheme="accent" variant="soft" size="sm">
                    LIVE
                </Badge>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,7rem),1fr))] gap-3">
                <div className="voxel-trough p-2 flex flex-col gap-1 min-w-0">
                    <span className="text-xs font-normal text-voxel-muted uppercase">Return</span>
                    <span
                        className={`font-mono text-sm font-bold tabular-nums ${
                            tone === 'success'
                                ? 'text-success'
                                : tone === 'danger'
                                  ? 'text-danger'
                                  : 'text-voxel-muted'
                        }`}
                    >
                        {formatPct(card.returnPct)}
                    </span>
                </div>
                <div className="voxel-trough p-2 flex flex-col gap-1 min-w-0">
                    <span className="text-xs font-normal text-voxel-muted uppercase">SPY</span>
                    <span className="font-mono text-sm font-bold tabular-nums text-voxel-ink">
                        {formatPct(card.spyReturnPct)}
                    </span>
                </div>
                <div className="voxel-trough p-2 flex flex-col gap-1 min-w-0">
                    <span className="text-xs font-normal text-voxel-muted uppercase">Open</span>
                    <span className="font-mono text-sm font-bold tabular-nums text-voxel-ink">
                        {card.openPositions}
                    </span>
                </div>
            </div>

            {card.lastAction?.reason ? (
                <p className="voxel-trough p-2 text-xs font-normal text-voxel-muted whitespace-pre-wrap break-words line-clamp-3">
                    {card.lastAction.reason}
                </p>
            ) : null}

            <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-2">
                <span className="font-mono text-xs font-normal text-voxel-muted truncate">
                    {modelLabel(card.resolvedModel)
                        ? `run on ${modelLabel(card.resolvedModel)}`
                        : 'no model recorded'}
                </span>
                <Button
                    variant="outline"
                    size="sm"
                    isLoading={isForking}
                    onClick={() => onFork(card.recipeId)}
                >
                    Fork
                </Button>
            </div>
        </Card>
    );
}

export function RecipeDeskHomePage({
    desk,
    leaderboard,
    onFork,
    forkingId,
    error,
}: RecipeDeskHomePageProps) {
    const cards = Array.isArray(desk?.cards) ? desk.cards : [];
    const feed = Array.isArray(desk?.feed) ? desk.feed : [];
    // Normalised at the route boundary; the guards here only protect a direct render
    // (tests, stories) from a partial payload.
    const boardRows: LeaderboardRow[] = Array.isArray(leaderboard?.rows) ? leaderboard.rows : [];
    const spySeries: EquityPoint[] = Array.isArray(leaderboard?.spy) ? leaderboard.spy : [];
    const windowDays = leaderboard?.windowDays ?? 30;
    const medianReturnPct = leaderboard?.medianReturnPct ?? null;

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
            <PageLayout maxWidth="xl" paddingY="tight" className="flex flex-col gap-6">
                <HomeHero
                    chart={<EquityChart rows={boardRows} spy={spySeries} windowDays={windowDays} />}
                    medianReturnPct={formatPct(medianReturnPct)}
                    windowDays={windowDays}
                />

                <section className="flex flex-col gap-3" aria-labelledby="portfolios-heading">
                    <SectionHeading className="text-sm">
                        <span id="portfolios-heading">Portfolio leaderboard</span>
                    </SectionHeading>
                    <TopPortfolios
                        rows={boardRows}
                        trackedCount={leaderboard?.trackedCount ?? null}
                        windowDays={windowDays}
                        degraded={leaderboard?.degraded ?? false}
                        starterNames={STARTER_RECIPES.map((template) => template.name)}
                    />
                    <p className="text-xs font-normal text-voxel-muted">
                        Start from a working recipe above. Two free backtests a day, three live
                        bots, no card, paper only.
                    </p>
                </section>

                {error ? (
                    <p role="alert" className="voxel-trough p-3 text-xs font-normal text-danger">
                        {error}
                    </p>
                ) : null}

                <section className="flex flex-col gap-4" aria-labelledby="desk-heading">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <SectionHeading className="text-sm">
                            <span id="desk-heading">Live desk</span>
                        </SectionHeading>
                        <p className="font-mono text-xs font-normal text-voxel-muted">
                            {desk.liveCount ?? 0} live · {desk.beatSpyCount ?? 0} beating SPY
                        </p>
                    </div>

                    {cards.length === 0 ? (
                        <EmptyState
                            title="No live recipes yet"
                            subtitle="The board fills as recipes run at 09:30, 12:30 and 15:30 ET. Start from a starter recipe and it will appear here once it trades."
                        />
                    ) : (
                        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4 items-stretch">
                            {cards.map((card) => (
                                <RecipeCard
                                    key={card.recipeId}
                                    card={card}
                                    onFork={onFork}
                                    isForking={forkingId === card.recipeId}
                                />
                            ))}
                        </div>
                    )}

                    {feed.length > 0 ? (
                        <div className="flex flex-col gap-2">
                            <SectionHeading className="text-sm">
                                <span id="feed-heading">Today</span>
                            </SectionHeading>
                            <ul className="flex flex-col gap-1">
                                {feed.map((item) => (
                                    <li
                                        key={`${item.recipeId}-${item.at}-${item.ticker}-${item.action}`}
                                        className="voxel-trough px-3 py-2 flex flex-wrap items-baseline gap-2 text-xs"
                                    >
                                        <span className="font-mono text-voxel-muted">
                                            {new Date(item.at).toLocaleTimeString('en-US', {
                                                hour: '2-digit',
                                                minute: '2-digit',
                                                timeZone: 'America/New_York',
                                            })}{' '}
                                            ET
                                        </span>
                                        <span className="font-bold text-voxel-ink">
                                            {item.action}
                                        </span>
                                        <span className="font-mono text-voxel-ink">
                                            {item.ticker}
                                        </span>
                                        <span className="text-voxel-muted break-words">
                                            {item.recipeName}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ) : null}
                </section>
            </PageLayout>
        </div>
    );
}
