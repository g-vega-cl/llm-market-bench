import { PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { createFileRoute } from '@tanstack/react-router';
import { createServerFn } from '@tanstack/react-start';
import {
    getHomePayload,
    normalizeDesk,
    normalizeLeaderboard,
} from '~/features/home/api/home-payload';
import { TopPortfolios } from '~/features/home/pages/TopPortfolios';
import { formatPct } from '~/features/playground/lib/proof';
import type { PublicBoardCard } from '~/features/recipes/api/public-board-api';
import { seo } from '~/lib/seo';

// A plain loader also runs in the browser, where the service-role admin client
// throws and the desk renders empty on client-side navigation.
const loadDesk = createServerFn({ method: 'GET' }).handler(async () => await getHomePayload());

export const Route = createFileRoute('/live-desk')({
    loader: async () => await loadDesk(),
    head: () => ({
        meta: [
            ...seo({
                title: 'Live desk — every public bot, losers included',
                description:
                    'Every bot running on Benchify with its return against SPY, beside the ranked agent portfolios and the worst performer.',
            }),
        ],
    }),
    component: LiveDeskRoute,
});

function tone(value: number | null): string {
    if (value === null) return 'text-voxel-muted';
    return value >= 0 ? 'text-success' : 'text-danger';
}

function BotRow({ card }: { card: PublicBoardCard }) {
    const action = card.lastAction
        ? `${card.lastAction.action} ${card.lastAction.ticker}`
        : 'no fills yet';
    return (
        <li className="voxel-trough flex flex-wrap items-baseline gap-x-3 gap-y-1 px-3 py-2 min-w-0">
            <span className="text-sm font-bold text-voxel-ink max-w-56 truncate">{card.name}</span>
            <span className={`font-mono text-xs font-normal tabular-nums ${tone(card.returnPct)}`}>
                {formatPct(card.returnPct)}
            </span>
            <span className="font-mono text-xs font-normal text-voxel-muted tabular-nums">
                vs SPY {formatPct(card.spyReturnPct)}
            </span>
            <span className="font-mono text-xs font-normal text-voxel-muted tabular-nums">
                {card.openPositions} open
            </span>
            <span className="text-xs font-normal text-voxel-muted">{action}</span>
        </li>
    );
}

function LiveDeskRoute() {
    const payload = (Route.useLoaderData() ?? {}) as Partial<
        Awaited<ReturnType<typeof getHomePayload>>
    >;
    const desk = normalizeDesk(payload.desk);
    const leaderboard = normalizeLeaderboard(payload.leaderboard);
    const cards = desk.cards;

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
            <PageLayout maxWidth="xl" paddingY="tight" className="flex flex-col gap-6">
                <header className="flex flex-col gap-1 pb-4 border-b-2 border-voxel-bevel-hi">
                    <h1 className="text-sm font-bold text-voxel-ink">Live desk</h1>
                    <p className="text-xs font-normal text-voxel-muted">
                        {desk.liveCount} live · {desk.beatSpyCount} beating SPY · losers are
                        published beside winners.
                    </p>
                </header>

                <section className="flex flex-col gap-2" aria-labelledby="bots-heading">
                    <SectionHeading className="text-sm">
                        <span id="bots-heading">Every running bot</span>
                    </SectionHeading>
                    {cards.length === 0 ? (
                        <p className="voxel-trough p-3 text-xs font-normal text-voxel-muted">
                            No bots are live yet. Run one from the playground and it appears here
                            after its first turn.
                        </p>
                    ) : (
                        <ul className="flex flex-col gap-1">
                            {cards.map((card) => (
                                <BotRow key={card.recipeId} card={card} />
                            ))}
                        </ul>
                    )}
                </section>

                <section className="flex flex-col gap-3" aria-labelledby="board-heading">
                    <SectionHeading className="text-sm">
                        <span id="board-heading">Agent portfolios, same window</span>
                    </SectionHeading>
                    <TopPortfolios
                        rows={leaderboard.rows}
                        medianReturnPct={leaderboard.medianReturnPct}
                        worst={leaderboard.worst}
                        spy={leaderboard.spy}
                        trackedCount={leaderboard.trackedCount}
                        windowDays={leaderboard.windowDays}
                        degraded={leaderboard.degraded}
                    />
                </section>
            </PageLayout>
        </div>
    );
}
