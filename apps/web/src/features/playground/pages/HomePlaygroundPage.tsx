import { PageLayout } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { Link } from '@tanstack/react-router';
import type { PublicDesk } from '~/features/recipes/api/public-board-api';
import { track } from '~/lib/analytics';
import { ProofStrip } from '../components/ProofStrip';
import { RecipePlayground } from '../components/RecipePlayground';
import { VoxelWorld } from '../components/VoxelWorld';
import { type Mood, moodAsOf, moodSentence, moodTone } from '../lib/mood';
import type { Proof } from '../lib/proof';

export interface HomePlaygroundPageProps {
    mood: Mood;
    proof: Proof;
    desk: PublicDesk;
    isAuthenticated: boolean;
    runsLeft: number | null;
    email?: string;
}

const FACTS = ['2 free backtests/day', '3 live bots', '0 lookahead', 'paper cash only'];

export function HomePlaygroundPage({
    mood,
    proof,
    desk,
    isAuthenticated,
    runsLeft,
    email,
}: HomePlaygroundPageProps) {
    const posthog = usePostHog();
    const asOf = moodAsOf(mood);

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
            <PageLayout maxWidth="xl" paddingY="tight" className="flex flex-col gap-6">
                <header className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,26rem),1fr))] gap-6 items-start pb-4 border-b-2 border-voxel-bevel-hi">
                    <div className="min-w-0 flex flex-col gap-4">
                        <p className="font-mono text-xs font-normal text-accent uppercase tracking-wide">
                            A bot builder, not a dashboard
                        </p>
                        <h1 className="text-lg font-bold text-voxel-ink text-balance">
                            Stack five blocks. Get a bot that decides every 30 minutes during market
                            hours.
                        </h1>
                        <p className="text-xs font-normal text-voxel-muted">
                            Weekdays 09:30–16:00 ET, market holidays excepted · decisions, not
                            guaranteed trades · paper cash only · every loser stays on the board.
                        </p>
                        <ul className="flex flex-wrap gap-2">
                            {FACTS.map((fact) => (
                                <li
                                    key={fact}
                                    className="voxel-trough px-2 py-1 font-mono text-xs font-normal text-voxel-muted whitespace-nowrap"
                                >
                                    {fact}
                                </li>
                            ))}
                        </ul>
                        <p className="text-xs font-normal text-voxel-muted">{moodSentence(mood)}</p>
                        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs font-normal">
                            <Link
                                to="/live-desk"
                                className="text-accent hover:underline whitespace-nowrap"
                            >
                                See every live bot →
                            </Link>
                            <Link
                                to="/recipes-demo"
                                className="text-voxel-muted hover:text-voxel-ink hover:underline whitespace-nowrap"
                            >
                                A finished backtest →
                            </Link>
                        </div>
                    </div>

                    <div className="min-w-0 flex flex-col gap-2">
                        <VoxelWorld tone={moodTone(mood)} />
                        {asOf ? (
                            <p className="font-mono text-xs font-normal text-voxel-muted">
                                Desk reading as of {asOf} ET
                            </p>
                        ) : null}
                    </div>
                </header>

                <RecipePlayground
                    isAuthenticated={isAuthenticated}
                    runsLeft={runsLeft}
                    email={email}
                    onEvent={(event, props) => track(posthog, event, props)}
                />

                <ProofStrip proof={proof} liveCount={desk.liveCount ?? 0} />
            </PageLayout>
        </div>
    );
}
