import { Link } from '@tanstack/react-router';

export type BotStageTab = 'overview' | 'live' | 'edit';

function subNavClass(active: boolean): string {
    if (active) {
        return 'voxel-btn inline-flex items-center px-3 py-1.5 text-sm font-bold bg-accent text-voxel-trough border-2 border-voxel-bevel-hi rounded-none whitespace-nowrap';
    }
    return 'voxel-btn inline-flex items-center px-3 py-1.5 text-sm font-bold bg-voxel-surface text-voxel-ink border-2 border-voxel-bevel-hi hover:bg-voxel-elevated rounded-none whitespace-nowrap';
}

export function BotStageSubNav({
    recipeId,
    activeTab,
    isOwner,
    markCurrent = true,
}: {
    recipeId: string;
    activeTab: BotStageTab;
    isOwner: boolean;
    /** Detail pages pass `false`: the chip styles as current but links to another URL. */
    markCurrent?: boolean;
}) {
    const current = (tab: BotStageTab) => (markCurrent && activeTab === tab ? 'page' : undefined);

    return (
        <nav
            aria-label="Bot views"
            className="voxel-trough bg-voxel-trough inline-flex flex-wrap items-center gap-2 p-2 rounded-none self-start max-w-full"
        >
            <Link
                to="/recipes/$recipeId"
                params={{ recipeId }}
                aria-current={current('overview')}
                className={subNavClass(activeTab === 'overview')}
            >
                Overview
            </Link>
            <Link
                to="/recipes/live/$recipeId"
                params={{ recipeId }}
                aria-current={current('live')}
                className={subNavClass(activeTab === 'live')}
            >
                Live Runs
            </Link>
            {isOwner ? (
                <Link
                    to="/recipes/$recipeId/edit"
                    params={{ recipeId }}
                    aria-current={current('edit')}
                    className={subNavClass(activeTab === 'edit')}
                >
                    Blueprint
                </Link>
            ) : null}
        </nav>
    );
}
