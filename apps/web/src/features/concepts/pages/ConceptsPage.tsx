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
        <div className="flex flex-col min-h-screen p-6 md:p-12">
            <div className="flex flex-col w-full">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold tracking-tight mb-2">Concept Cluster Map</h1>
                    <p className="text-gray-500 text-lg">
                        Semantic visualization of market narratives. Position represents semantic
                        similarity (PCA), color represents momentum velocity.
                    </p>
                </div>

                <ConceptMap data={data} />

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8 border-t border-gray-100 pt-8">
                    <div>
                        <h3 className="font-semibold mb-2 flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full bg-gradient-to-r from-blue-500 via-green-500 to-red-500" />
                            Color: Momentum Velocity
                        </h3>
                        <p className="text-sm text-gray-500">
                            Represents the acceleration of mentions (Last 7 Days vs 30-Day Avg).
                            <br />
                            <span className="text-blue-600 font-medium">Cool Colors</span> =
                            Stable/Fading
                            <br />
                            <span className="text-red-600 font-medium">Hot Colors</span> =
                            Emerging/Viral
                        </p>
                    </div>
                    <div>
                        <h3 className="font-semibold mb-2 flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full bg-gray-400" />
                            Size: Volume
                        </h3>
                        <p className="text-sm text-gray-500">
                            Larger circles indicate a higher total citation count across all
                            newsletters (90-day history).
                        </p>
                    </div>
                    <div>
                        <h3 className="font-semibold mb-2 flex items-center gap-2">
                            <span className="w-4 h-4 text-xs border border-gray-300 flex items-center justify-center rounded">
                                XY
                            </span>
                            Position: Semantic Similarity
                        </h3>
                        <p className="text-sm text-gray-500">
                            Concepts appearing close together share semantic meaning in the vector
                            space (reduced from 768 dimensions via PCA).
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
