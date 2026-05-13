import { usePostHog } from '@posthog/react';
import { useSuspenseQuery } from '@tanstack/react-query';
import * as React from 'react';
import { CauseAndEffectList } from '../components/CauseAndEffectList';
import { causeAndEffectQueries } from '../queries/options';

interface CauseAndEffectPageProps {
    initialData: any[];
    fetchFn: () => Promise<any[]>;
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
        <div className="flex flex-col min-h-screen px-6 md:px-12 py-12">
            <div className="flex flex-col w-full">
                <header className="mb-12">
                    <h1 className="text-4xl font-bold text-zinc-400 mb-4 tracking-tight">
                        Cause & Effect Library
                    </h1>
                    <p className="text-zinc-400 text-lg leading-relaxed">
                        A historical playbook of market reactions. Explore why the market moved
                        following specific global events and use it as a frame for the future.
                    </p>
                </header>

                <CauseAndEffectList entries={(data as any[]) || []} />
            </div>
        </div>
    );
}
