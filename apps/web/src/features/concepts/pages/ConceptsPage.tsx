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
                    <SectionHeading gradient="ai">Concept Cluster Map</SectionHeading>
                    <p className="text-zinc-500 text-lg mt-2">
                        Semantic visualization of market narratives. Position represents semantic
                        similarity (PCA), color represents momentum velocity.
                    </p>
                </header>

                <ConceptMap data={data} />

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8 border-t border-zinc-200 dark:border-zinc-800 pt-8">
                    <div>
                        <h3 className="font-semibold mb-2 flex items-center gap-2 text-zinc-800 dark:text-zinc-200">
                            <span className="w-3 h-3 rounded-full bg-gradient-to-r from-blue-500 via-green-500 to-red-500" />
                            Color: Momentum Velocity
                        </h3>
                        <p className="text-sm text-zinc-500">
                            Represents the acceleration of mentions (Last 7 Days vs 30-Day Avg).
                            <br />
                            <span className="text-accent font-medium">Cool Colors</span> =
                            Stable/Fading
                            <br />
                            <span className="text-danger font-medium">Hot Colors</span> =
                            Emerging/Viral
                        </p>
                    </div>
                    <div>
                        <h3 className="font-semibold mb-2 flex items-center gap-2 text-zinc-800 dark:text-zinc-200">
                            <span className="w-3 h-3 rounded-full bg-zinc-400" />
                            Size: Volume
                        </h3>
                        <p className="text-sm text-zinc-500">
                            Larger circles indicate a higher total citation count across all
                            newsletters (90-day history).
                        </p>
                    </div>
                    <div>
                        <h3 className="font-semibold mb-2 flex items-center gap-2 text-zinc-800 dark:text-zinc-200">
                            <span className="w-4 h-4 text-xs border border-zinc-300 dark:border-zinc-600 flex items-center justify-center rounded text-zinc-600 dark:text-zinc-400">
                                XY
                            </span>
                            Position: Semantic Similarity
                        </h3>
                        <p className="text-sm text-zinc-500">
                            Concepts appearing close together share semantic meaning in the vector
                            space (reduced from 768 dimensions via PCA).
                        </p>
                    </div>
                </div>
            </PageLayout>
        </div>
    );
}
