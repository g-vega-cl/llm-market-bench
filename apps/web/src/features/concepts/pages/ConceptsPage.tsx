import { PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import type { Concept } from '../components/ConceptMap';
import { ConceptMap } from '../components/ConceptMap';
import { conceptsQueries } from '../queries/options';

export type { Concept };

interface ConceptsPageProps {
    initialData: Concept[];
    fetchFn: () => Promise<Concept[]>;
}

export function ConceptsPage({ initialData, fetchFn }: ConceptsPageProps) {
    const { data } = useSuspenseQuery({
        ...conceptsQueries.list({ fetchFn }),
        initialData,
    });

    return (
        <div className="min-h-screen">
            <PageLayout>
                <header className="mb-8">
                    <SectionHeading gradient="ai">Concept Tracker</SectionHeading>
                    <p className="text-zinc-500 text-lg mt-2">
                        Track trending, high-volume, and emerging market concepts extracted from
                        news feeds and decision logs.
                    </p>
                </header>

                <ConceptMap data={data} />

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8 border-t border-zinc-200 dark:border-zinc-800 pt-8">
                    <div>
                        <h3 className="font-semibold mb-2 flex items-center gap-2 text-zinc-800 dark:text-zinc-200">
                            <span className="w-3 h-3 rounded-full bg-accent" />
                            Dynamic Tabs
                        </h3>
                        <p className="text-sm text-zinc-500">
                            Switch between tabs to change sorting order:
                            <br />
                            <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                                Trending
                            </span>
                            : Mentions accelerating velocity.
                            <br />
                            <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                                Most Mentioned
                            </span>
                            : Highest overall volume.
                            <br />
                            <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                                Newest
                            </span>
                            : Chronological discovery.
                        </p>
                    </div>
                    <div>
                        <h3 className="font-semibold mb-2 flex items-center gap-2 text-zinc-800 dark:text-zinc-200">
                            <span className="w-3 h-3 rounded-full bg-success" />
                            Status Badges
                        </h3>
                        <p className="text-sm text-zinc-500">
                            Visual status indicators categorized by velocity score:
                            <br />
                            <span className="text-danger font-medium">Accelerating</span>: Velocity
                            &ge; 3.0 (rapidly gaining traction).
                            <br />
                            <span className="text-success font-medium">Stable</span>: Velocity &ge;
                            1.0 (moderate persistent interest).
                            <br />
                            <span className="text-zinc-400 font-medium">Cooling</span>: Velocity
                            &lt; 1.0 (fading mentions).
                        </p>
                    </div>
                    <div>
                        <h3 className="font-semibold mb-2 flex items-center gap-2 text-zinc-800 dark:text-zinc-200">
                            <span className="w-3 h-3 rounded-full bg-blue-500" />
                            Timeline & Lifespan
                        </h3>
                        <p className="text-sm text-zinc-500">
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
