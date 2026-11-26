import { Badge, Card, PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { STARTER_RECIPES } from '../starter-templates';
import type { PushStrategy } from '../types';

const BLOCK_ORDER = ['prompt', 'news', 'memories', 'technicals', 'output_format'] as const;

function LockIcon() {
    return (
        <svg
            className="w-3.5 h-3.5 shrink-0"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
    );
}

function promptExcerpt(strategy: PushStrategy): string {
    const prompt = strategy.stages[0]?.blocks.find((block) => block.type === 'prompt');
    if (!prompt || prompt.type !== 'prompt') return 'Trades on the block filters alone.';
    const text = prompt.text.replace(/\s+/g, ' ').trim();
    return text.length > 180 ? `${text.slice(0, 177)}...` : text;
}

function blocksOf(strategy: PushStrategy) {
    const types = new Set(strategy.stages[0]?.blocks.map((block) => block.type) ?? []);
    return BLOCK_ORDER.filter((type) => types.has(type));
}

export interface RecipeGalleryPageProps {
    templates?: PushStrategy[];
}

/**
 * Public face of /recipes. A logged-out visitor sees what a recipe actually is —
 * the prompt, the filters, one LLM call — before being asked to sign in.
 */
export function RecipeGalleryPage({ templates = STARTER_RECIPES }: RecipeGalleryPageProps) {
    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
            <PageLayout maxWidth="xl" className="flex flex-col gap-8">
                <header className="flex flex-col gap-3 pb-4 border-b-2 border-voxel-bevel-hi">
                    <SectionHeading className="text-sm">Strategy recipes</SectionHeading>
                    <p className="text-xs font-normal text-voxel-muted max-w-prose">
                        Each recipe is a single LLM call over point-in-time news, memories and
                        technical filters. Click any locked starter below to sign in with Google and
                        customize it, or build your own bot from one sentence.
                    </p>
                    <div className="flex flex-wrap items-center gap-4">
                        <Link
                            to="/build"
                            className="voxel-btn inline-flex items-center px-4 py-2 text-sm font-bold bg-accent text-voxel-trough hover:bg-accent-hover"
                        >
                            Start Building Your Bot →
                        </Link>
                        <Link
                            to="/recipes-demo"
                            className="text-xs font-normal text-voxel-muted underline underline-offset-4 hover:text-accent"
                        >
                            or see a sample backtest
                        </Link>
                    </div>
                </header>

                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4 items-stretch">
                    {templates.map((template) => (
                        <Link
                            key={template.name}
                            to="/login"
                            search={{
                                redirect: `/build?starter=${encodeURIComponent(template.name)}`,
                            }}
                            className="block h-full"
                        >
                            <Card padding="md" className="h-full min-w-0 flex flex-col gap-3">
                                <div className="flex flex-col gap-1 pb-2 border-b-2 border-voxel-bevel-hi">
                                    <div className="flex items-start justify-between gap-2">
                                        <span className="text-sm font-bold text-voxel-ink break-words">
                                            {template.name}
                                        </span>
                                        <Badge
                                            colorScheme="neutral"
                                            variant="soft"
                                            size="sm"
                                            className="shrink-0 inline-flex items-center gap-1"
                                        >
                                            <LockIcon />
                                            <span>Sign in</span>
                                        </Badge>
                                    </div>
                                    <span className="text-xs font-normal text-voxel-muted">
                                        Live: 30m · Backtest: {template.cadence} · one LLM call
                                    </span>
                                </div>
                                <div className="flex flex-wrap gap-1">
                                    {blocksOf(template).map((type) => (
                                        <Badge
                                            key={type}
                                            colorScheme="accent"
                                            variant="soft"
                                            size="sm"
                                        >
                                            {type}
                                        </Badge>
                                    ))}
                                </div>
                                <p className="voxel-trough p-2 text-xs font-normal text-voxel-muted whitespace-pre-wrap break-words line-clamp-3">
                                    {promptExcerpt(template)}
                                </p>
                                <span className="mt-auto text-xs font-normal text-accent">
                                    Sign in to customize &amp; run backtest →
                                </span>
                            </Card>
                        </Link>
                    ))}
                </div>

                <p className="text-xs font-normal text-voxel-muted">
                    Two free backtests a day, three live bots. Paper only, no brokerage account.
                </p>
            </PageLayout>
        </div>
    );
}
