import {
    Badge,
    Button,
    EmptyState,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import type { PublicBoardCard, PublicDesk } from '~/features/recipes/api/public-board-api';
import type {
    EquityPoint,
    LeaderboardRow,
    PortfolioLeaderboard,
} from '../api/portfolio-leaderboard';
import { BuildProof } from './BuildProof';
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

function returnTone(value: number | null): string {
    if (value === null) return 'text-voxel-muted';
    return value >= 0 ? 'text-success' : 'text-danger';
}

/**
 * One line per bot. The trough grid and the last-action paragraph were four
 * numbers and a sentence in 220px; a builder desk should read like a tape.
 */
function BotRow({
    card,
    onFork,
    isForking,
}: {
    card: PublicBoardCard;
    onFork: (recipeId: string) => void;
    isForking: boolean;
}) {
    const model = modelLabel(card.resolvedModel);

    return (
        <li className="voxel-trough px-3 py-2 flex flex-wrap items-center gap-x-3 gap-y-1 min-w-0">
            <Badge colorScheme="accent" variant="soft" size="sm">
                LIVE
            </Badge>
            <span className="text-sm font-bold text-voxel-ink shrink-0 max-w-56 truncate">
                {card.name}
            </span>
            {card.description ? (
                <span className="text-xs font-normal text-voxel-muted flex-1 min-w-40 truncate">
                    “{card.description}”
                </span>
            ) : (
                <span className="text-xs font-normal text-voxel-muted flex-1 min-w-40 truncate">
                    {card.lastAction
                        ? `${card.lastAction.action} ${card.lastAction.ticker}`
                        : 'no fills yet'}
                </span>
            )}
            <span
                className={`font-mono text-xs font-normal tabular-nums shrink-0 ${returnTone(card.returnPct)}`}
            >
                {formatPct(card.returnPct)}
            </span>
            <span className="font-mono text-xs font-normal text-voxel-muted tabular-nums shrink-0">
                vs SPY {formatPct(card.spyReturnPct)}
            </span>
            <span className="font-mono text-xs font-normal text-voxel-muted tabular-nums shrink-0">
                {card.openPositions} open
            </span>
            <span className="font-mono text-xs font-normal text-voxel-muted shrink-0 max-w-40 truncate">
                {model ? `run on ${model}` : 'no model recorded'}
            </span>
            <Button
                variant="outline"
                size="sm"
                isLoading={isForking}
                onClick={() => onFork(card.recipeId)}
            >
                Fork
            </Button>
        </li>
    );
}

function StarterTemplatesStrip() {
    return (
        <div className="voxel-trough p-3 flex flex-wrap items-baseline justify-between gap-2 min-w-0">
            <span className="text-xs font-normal text-voxel-muted">
                Might as well try it out — fork a live bot above or pick a starter strategy in the
                studio.
            </span>
            <Link
                to="/recipes"
                className="text-xs font-normal text-accent hover:underline whitespace-nowrap"
            >
                Browse starter recipes →
            </Link>
        </div>
    );
}

function TodayFeed({ feed }: { feed: PublicDesk['feed'] }) {
    if (feed.length === 0) return null;
    return (
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
                        <span className="font-mono text-voxel-muted whitespace-nowrap">
                            {new Date(item.at).toLocaleTimeString('en-US', {
                                hour: '2-digit',
                                minute: '2-digit',
                                timeZone: 'America/New_York',
                            })}{' '}
                            ET
                        </span>
                        <span className="font-bold text-voxel-ink">{item.action}</span>
                        <span className="font-mono text-voxel-ink">{item.ticker}</span>
                        <span className="text-voxel-muted break-words">{item.recipeName}</span>
                    </li>
                ))}
            </ul>
        </div>
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

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
            <PageLayout maxWidth="xl" paddingY="tight" className="flex flex-col gap-6">
                <HomeHero
                    proof={
                        <BuildProof
                            spotlight={desk.spotlight ?? null}
                            onFork={onFork}
                            isForking={Boolean(
                                desk.spotlight && forkingId === desk.spotlight.recipeId,
                            )}
                        />
                    }
                />

                <section className="flex flex-col gap-3" aria-labelledby="portfolios-heading">
                    <SectionHeading className="text-sm">
                        <span id="portfolios-heading">Portfolio leaderboard</span>
                    </SectionHeading>
                    <TopPortfolios
                        rows={boardRows}
                        medianReturnPct={leaderboard?.medianReturnPct ?? null}
                        worst={leaderboard?.worst ?? null}
                        spy={spySeries}
                        trackedCount={leaderboard?.trackedCount ?? null}
                        windowDays={windowDays}
                        degraded={leaderboard?.degraded ?? false}
                    />
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
                        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs font-normal">
                            <p className="font-mono text-voxel-muted whitespace-nowrap">
                                {desk.liveCount ?? 0} live · {desk.beatSpyCount ?? 0} beating SPY
                            </p>
                            <Link
                                to="/audits"
                                className="text-voxel-muted hover:text-voxel-ink hover:underline whitespace-nowrap"
                            >
                                Trade audits →
                            </Link>
                        </div>
                    </div>

                    {cards.length === 0 ? (
                        <EmptyState
                            title="No live recipes yet"
                            subtitle="The board fills as recipes run every 30 minutes during market hours (09:30–16:00 ET). Start from a starter recipe below and it will appear here once it trades."
                        />
                    ) : (
                        <ul className="flex flex-col gap-1">
                            {cards.map((card) => (
                                <BotRow
                                    key={card.recipeId}
                                    card={card}
                                    onFork={onFork}
                                    isForking={forkingId === card.recipeId}
                                />
                            ))}
                        </ul>
                    )}

                    <StarterTemplatesStrip />

                    <TodayFeed feed={feed} />
                </section>
            </PageLayout>
        </div>
    );
}
