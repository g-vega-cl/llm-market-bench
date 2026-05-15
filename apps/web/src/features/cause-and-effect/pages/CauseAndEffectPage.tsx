import { PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useSuspenseQuery } from '@tanstack/react-query';
import * as React from 'react';
import type { CauseAndEffectEntry } from '../api/fetch-cause-and-effect';
import { CauseAndEffectList } from '../components/CauseAndEffectList';
import { causeAndEffectQueries } from '../queries/options';

interface CauseAndEffectPageProps {
    initialData: CauseAndEffectEntry[];
    fetchFn: () => Promise<CauseAndEffectEntry[]>;
}

export function CauseAndEffectPage({ initialData, fetchFn }: CauseAndEffectPageProps) {
    const posthog = usePostHog();

    const { data } = useSuspenseQuery({
        ...causeAndEffectQueries.list({ fetchFn }),
        initialData,
    });

    React.useEffect(() => {
        posthog.capture('cause_and_effect_viewed');
    }, [posthog]);

    return (
        <div className="min-h-screen">
            <PageLayout>
                <header className="mb-12">
                    <SectionHeading gradient="catalyst">Cause & Effect Library</SectionHeading>
                    <p className="text-zinc-400 text-lg leading-relaxed mt-2">
                        A historical playbook of market reactions. Explore why the market moved
                        following specific global events and use it as a frame for the future.
                    </p>
                </header>

                <CauseAndEffectList entries={data || []} />
            </PageLayout>
        </div>
    );
}
