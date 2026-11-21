import { Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import type { PublicSpotlight } from '~/features/recipes/api/public-board-api';
import { formatPct } from './format-pct';

export interface BuildProofProps {
    spotlight: PublicSpotlight | null;
    onFork: (recipeId: string) => void;
    isForking?: boolean;
}

/**
 * The hero's evidence is the product's own artifact: a sentence someone typed,
 * the graph it compiled to, and what that bot has done since. A chart of other
 * people's portfolios argues for the benchmark, not for the builder.
 */
export function BuildProof({ spotlight, onFork, isForking = false }: BuildProofProps) {
    return (
        <Card padding="md" className="h-full min-w-0 flex flex-col gap-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
                <SectionHeading>Built from one sentence</SectionHeading>
                {spotlight ? (
                    <span className="font-mono text-xs font-normal text-voxel-muted whitespace-nowrap">
                        running live
                    </span>
                ) : null}
            </div>

            {spotlight ? (
                <>
                    <p className="text-sm font-bold text-voxel-ink break-words">
                        “{spotlight.prompt}”
                    </p>

                    <div className="flex flex-col gap-2">
                        <span className="text-xs font-normal text-voxel-muted">
                            compiled to a working recipe
                        </span>
                        <ul className="flex flex-wrap gap-2">
                            {spotlight.blocks.map((block) => (
                                <li
                                    key={block}
                                    className="voxel-trough px-2 py-1 text-xs font-normal text-voxel-muted"
                                >
                                    {block}
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className="mt-auto flex flex-wrap items-baseline justify-between gap-2 pt-2 border-t-2 border-voxel-bevel-hi">
                        <span className="font-mono text-xs font-normal text-voxel-muted truncate min-w-0">
                            {spotlight.name}
                        </span>
                        <span className="font-mono text-sm font-bold text-voxel-ink tabular-nums whitespace-nowrap">
                            {formatPct(spotlight.returnPct)} vs SPY{' '}
                            {formatPct(spotlight.spyReturnPct)}
                        </span>
                    </div>

                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            isLoading={isForking}
                            onClick={() => onFork(spotlight.recipeId)}
                        >
                            Fork this bot
                        </Button>
                        <Link
                            to="/recipes-demo"
                            className="text-xs font-normal text-accent hover:underline whitespace-nowrap"
                        >
                            See a sample backtest →
                        </Link>
                    </div>
                </>
            ) : (
                <div className="flex flex-col gap-4 mt-auto">
                    <p className="text-xs font-normal text-voxel-muted">
                        No public bot has a written prompt yet. Describe yours above and you will be
                        the first on this panel.
                    </p>
                    <div className="flex flex-wrap items-baseline gap-2">
                        <Link
                            to="/recipes-demo"
                            className="text-xs font-normal text-accent hover:underline whitespace-nowrap"
                        >
                            See a sample backtest →
                        </Link>
                    </div>
                </div>
            )}
        </Card>
    );
}
