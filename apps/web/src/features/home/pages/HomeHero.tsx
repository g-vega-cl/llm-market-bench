import { Button, Input } from '@llm-market-bench/ui-design-system';
import { Link, useRouter } from '@tanstack/react-router';
import { type FormEvent, type ReactNode, useState } from 'react';

export interface HomeHeroProps {
    /** The product's own artifact: a prompt, the graph it compiled to, its result. */
    proof: ReactNode;
}

/**
 * Above-the-fold block: headline, idea form and live proof share one row
 * on wide screens and stack when the container is narrow (no viewport
 * breakpoints, per design spec §2).
 */
export function HomeHero({ proof }: HomeHeroProps) {
    const router = useRouter();
    const [idea, setIdea] = useState('');

    const submitIdea = (event: FormEvent) => {
        event.preventDefault();
        void router.navigate({ to: '/build', search: { idea: idea.trim() || undefined } });
    };

    return (
        <header className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,26rem),1fr))] gap-6 items-stretch pb-4 border-b-2 border-voxel-bevel-hi">
            <div className="min-w-0 flex flex-col gap-4 justify-between">
                <p className="font-mono text-xs font-normal text-accent uppercase tracking-wide">
                    Verifiable AI trading · losers published next to winners
                </p>
                <h1 className="text-lg font-bold text-voxel-ink text-balance">
                    Describe a trading bot. It runs live 3× a day with public receipts.
                </h1>
                <p className="text-xs font-normal text-voxel-muted">
                    Every bot is one inspectable LLM call reading only news and market history
                    available at that exact minute—zero lookahead. Paper cash only, two free
                    backtests a day, and every trade and loser stays public.
                </p>
                <form className="flex flex-wrap items-stretch gap-2" onSubmit={submitIdea}>
                    <div className="flex-1 basis-64 min-w-0">
                        <Input
                            aria-label="Describe your strategy"
                            placeholder="Buy chipmakers when AI capex news turns positive, exit on guidance cuts"
                            value={idea}
                            onChange={(event) => setIdea(event.target.value)}
                            maxLength={280}
                        />
                    </div>
                    <Button type="submit" variant="solid" size="md">
                        Build it
                    </Button>
                </form>
                <div className="flex flex-col gap-2">
                    <ul className="flex flex-wrap gap-2">
                        {[
                            '2 free backtests/day',
                            '3 live bots',
                            '0 lookahead',
                            'paper cash only',
                        ].map((fact) => (
                            <li
                                key={fact}
                                className="voxel-trough px-2 py-1 font-mono text-xs font-normal text-voxel-muted whitespace-nowrap"
                            >
                                {fact}
                            </li>
                        ))}
                    </ul>
                    <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs font-normal">
                        <Link
                            to="/recipes-demo"
                            className="text-accent hover:underline whitespace-nowrap"
                        >
                            See a finished backtest →
                        </Link>
                        <Link
                            to="/reasoning"
                            className="text-voxel-muted hover:text-voxel-ink hover:underline whitespace-nowrap"
                        >
                            Read live reasoning logs →
                        </Link>
                    </div>
                </div>
            </div>

            {proof}
        </header>
    );
}
