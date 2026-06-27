import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { createFileRoute, Link } from '@tanstack/react-router';

export const Route = createFileRoute('/_authed/profile')({
    component: ProfileComponent,
});

function ProfileComponent() {
    const { user } = Route.useRouteContext();

    return (
        <main className="container mx-auto px-4 py-12 max-w-4xl">
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8 shadow-sm">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 pb-8 border-b border-zinc-200 dark:border-zinc-800">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                                User Profile
                            </h1>
                            <Badge variant="soft" colorScheme="success" size="sm">
                                Authenticated
                            </Badge>
                        </div>
                        <p className="text-zinc-500 dark:text-zinc-400 text-sm">
                            Manage your account settings and preferences
                        </p>
                    </div>
                    <Link to="/logout">
                        <Button variant="ghost" colorScheme="danger" size="sm">
                            Log out
                        </Button>
                    </Link>
                </div>

                <div className="mt-8 space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="p-5 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/60 dark:border-zinc-700/50">
                            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                                Email Address
                            </h2>
                            <p className="text-base font-medium text-zinc-900 dark:text-zinc-100">
                                {user?.email}
                            </p>
                        </div>

                        <div className="p-5 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/60 dark:border-zinc-700/50">
                            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                                Account Status
                            </h2>
                            <p className="text-base font-medium text-emerald-600 dark:text-emerald-400">
                                Active & Verified
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}
