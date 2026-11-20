import { Button, Card, Input, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useRouter } from '@tanstack/react-router';
import { type FormEvent, type ReactNode, useState } from 'react';

export interface HomeHeroProps {
    chart: ReactNode;
    medianReturnPct: string;
    windowDays: number;
}

/**
 * Above-the-fold block: headline, idea form and the equity chart share one row
 * on wide screens and stack when the container is narrow (no viewport
 * breakpoints, per design spec §2).
 */
export function HomeHero({ chart, medianReturnPct, windowDays }: HomeHeroProps) {
    const router = useRouter();
    const [idea, setIdea] = useState('');

    const submitIdea = (event: FormEvent) => {
        event.preventDefault();
        void router.navigate({ to: '/build', search: { idea: idea.trim() || undefined } });
    };

    return (
        <header className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,26rem),1fr))] gap-6 items-stretch pb-4 border-b-2 border-voxel-bevel-hi">
            <div className="min-w-0 flex flex-col gap-3 justify-between">
                <p className="font-mono text-xs font-normal text-accent uppercase tracking-wide">
                    Paper trading · three runs a day · no brokerage
                </p>
                <h1 className="text-lg font-bold text-voxel-ink text-balance">
                    Describe a trading bot. It runs three times a day on point-in-time news.
                </h1>
                <p className="text-xs font-normal text-voxel-muted">
                    Every recipe is one LLM call over the same news corpus and memories the
                    benchmark agents trade. Paper cash only, no brokerage account, and we publish
                    the losers next to the winners.
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
                <ul className="flex flex-wrap gap-2">
                    {['3 runs a day', 'paper cash only', '0 brokerage'].map((fact) => (
                        <li
                            key={fact}
                            className="voxel-trough px-2 py-1 font-mono text-xs font-normal text-voxel-muted"
                        >
                            {fact}
                        </li>
                    ))}
                </ul>
            </div>

            <Card padding="md" className="h-full min-w-0 flex flex-col gap-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <SectionHeading>Top 5 portfolios</SectionHeading>
                    <span className="font-mono text-xs font-normal text-voxel-muted">
                        board median {medianReturnPct} · {windowDays}d
                    </span>
                </div>
                {chart}
            </Card>
        </header>
    );
}
