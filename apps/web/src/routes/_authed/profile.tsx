import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { createFileRoute, Link } from '@tanstack/react-router';

export const Route = createFileRoute('/_authed/profile')({
    component: ProfileComponent,
});

function ProfileComponent() {
    const { user } = Route.useRouteContext();

    return (
        <main className="container mx-auto px-4 py-12 max-w-4xl">
            <div className="bg-zinc-900 border border-zinc-800 rounded-none p-8 shadow-sm flex flex-col gap-8">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 pb-8 border-b border-zinc-800">
                    <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-3">
                            <h1 className="text-lg font-bold font-display uppercase tracking-wider text-zinc-100">
                                User Profile
                            </h1>
                            <Badge variant="soft" colorScheme="success" size="sm" radius="none">
                                Authenticated
                            </Badge>
                        </div>
                        <p className="text-zinc-400 text-xs font-normal">
                            Manage your account settings and preferences
                        </p>
                    </div>
                    <Link to="/logout">
                        <Button variant="ghost" colorScheme="danger" size="sm">
                            Log out
                        </Button>
                    </Link>
                </div>

                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-6 items-stretch">
                    <div className="p-5 rounded-none bg-zinc-800/50 border border-zinc-700/50 shadow-sm flex flex-col justify-between gap-2">
                        <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                            Email Address
                        </h2>
                        <p className="text-sm font-bold text-zinc-100 font-mono">{user?.email}</p>
                    </div>

                    <div className="p-5 rounded-none bg-zinc-800/50 border border-zinc-700/50 shadow-sm flex flex-col justify-between gap-2">
                        <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                            Account Status
                        </h2>
                        <p className="text-sm font-bold text-emerald-400">Active &amp; Verified</p>
                    </div>
                </div>
            </div>
        </main>
    );
}
