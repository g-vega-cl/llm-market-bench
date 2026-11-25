import { Link } from '@tanstack/react-router';

/** Every bot page is one of these tabs; the chip row is the navigation. */
export type BotStageTab = 'overview' | 'performance' | 'behavior' | 'live' | 'edit';

/** How the active chip announces itself. Hubs and detail pages both use `page`. */
export type BotStageCurrentMode = 'page' | 'item' | 'none';

function subNavClass(active: boolean): string {
    if (active) {
        return 'voxel-btn inline-flex items-center px-3 py-1.5 text-sm font-bold bg-accent text-voxel-trough border-2 border-voxel-bevel-hi rounded-none whitespace-nowrap';
    }
    return 'voxel-btn inline-flex items-center px-3 py-1.5 text-sm font-bold bg-voxel-surface text-voxel-ink border-2 border-voxel-bevel-hi hover:bg-voxel-elevated rounded-none whitespace-nowrap';
}

/**
 * The bot's tab bar: Overview · Performance · Behaviour · Live Runs · Blueprint.
 *
 * Each chip is a real page, so a chip's href is the URL it claims: `aria-current`
 * says `page`, not `true`. Before this row carried the detail pages, Overview and
 * Live Runs were hubs whose panels sat behind a "→" link at the bottom of a card,
 * which is the link readers had to find to see anything.
 */
export function BotStageSubNav({
    recipeId,
    activeTab,
    isOwner,
    currentMode = 'page',
}: {
    recipeId: string;
    activeTab: BotStageTab;
    isOwner: boolean;
    currentMode?: BotStageCurrentMode;
}) {
    const current = (tab: BotStageTab) => {
        if (activeTab !== tab) return undefined;
        if (currentMode === 'none') return undefined;
        return currentMode === 'page' ? 'page' : 'true';
    };

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
                to="/recipes/$recipeId/performance"
                params={{ recipeId }}
                aria-current={current('performance')}
                className={subNavClass(activeTab === 'performance')}
            >
                Performance
            </Link>
            <Link
                to="/recipes/$recipeId/behavior"
                params={{ recipeId }}
                aria-current={current('behavior')}
                className={subNavClass(activeTab === 'behavior')}
            >
                Behaviour
            </Link>
            <Link
                to="/recipes/live/$recipeId/runs"
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
