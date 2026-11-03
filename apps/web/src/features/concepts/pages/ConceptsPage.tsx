import { PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import type { Concept, ConceptMemory } from '../api/fetch-concepts';
import { ConceptMap } from '../components/ConceptMap';
import { conceptsQueries } from '../queries/options';

export type { Concept };

interface ConceptsPageProps {
    initialData: Concept[];
    fetchFn: () => Promise<Concept[]>;
    fetchMemoriesFn: (conceptId: string) => Promise<ConceptMemory[]>;
}

export function ConceptsPage({ initialData, fetchFn, fetchMemoriesFn }: ConceptsPageProps) {
    const { data } = useSuspenseQuery({
        ...conceptsQueries.list({ fetchFn }),
        initialData,
    });

    return (
        <div className="min-h-screen">
            <PageLayout>
                <header className="flex flex-col gap-1">
                    <SectionHeading gradient="ai">Concept Tracker</SectionHeading>
                    <p className="text-boxel-muted text-xs font-normal m-0">
                        Track trending, high-volume, and emerging market concepts extracted from
                        news feeds and decision logs.
                    </p>
                </header>

                <ConceptMap data={data} fetchMemoriesFn={fetchMemoriesFn} />

                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-6 border-t border-zinc-200 dark:border-zinc-800 pt-6 items-stretch">
                    <div className="flex flex-col gap-2">
                        <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-800 dark:text-zinc-200 m-0">
                            <span className="w-2.5 h-2.5 rounded-none bg-accent shrink-0" />
                            Dynamic Tabs
                        </h3>
                        <p className="text-xs font-normal text-zinc-500 m-0 leading-relaxed">
                            Switch between tabs to change sorting order:
                            <br />
                            <span className="font-bold text-zinc-700 dark:text-zinc-300">
                                Trending
                            </span>
                            : Mentions accelerating velocity.
                            <br />
                            <span className="font-bold text-zinc-700 dark:text-zinc-300">
                                Most Mentioned
                            </span>
                            : Highest overall volume.
                            <br />
                            <span className="font-bold text-zinc-700 dark:text-zinc-300">
                                Newest
                            </span>
                            : Chronological discovery.
                            <br />
                            <span className="font-bold text-amber-600 dark:text-amber-400">
                                ⚡ Keep an Eye
                            </span>
                            : Imminent and digesting calendar triggers linked to high-velocity
                            narratives.
                        </p>
                    </div>
                    <div className="flex flex-col gap-2">
                        <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-800 dark:text-zinc-200 m-0">
                            <span className="w-2.5 h-2.5 rounded-none bg-success shrink-0" />
                            Status Badges
                        </h3>
                        <p className="text-xs font-normal text-zinc-500 m-0 leading-relaxed">
                            Visual status indicators categorized by velocity score:
                            <br />
                            <span className="text-danger font-bold">Accelerating</span>: Velocity
                            &ge; 3.0 (rapidly gaining traction).
                            <br />
                            <span className="text-success font-bold">Stable</span>: Velocity &ge;
                            1.0 (moderate persistent interest).
                            <br />
                            <span className="text-zinc-400 font-bold">Cooling</span>: Velocity &lt;
                            1.0 (fading mentions).
                        </p>
                    </div>
                    <div className="flex flex-col gap-2">
                        <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-800 dark:text-zinc-200 m-0">
                            <span className="w-2.5 h-2.5 rounded-none bg-blue-500 shrink-0" />
                            Timeline & Lifespan
                        </h3>
                        <p className="text-xs font-normal text-zinc-500 m-0 leading-relaxed">
                            Click on any row to expand it inline. This reveals the first seen date,
                            the last seen date, the lifespan duration of the narrative, and its
                            original vector space coordinates.
                        </p>
                    </div>
                </div>
            </PageLayout>
        </div>
    );
}
