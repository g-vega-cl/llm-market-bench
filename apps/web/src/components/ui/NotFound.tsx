import { Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';

export function NotFound({ children }: { children?: React.ReactNode }) {
    return (
        <div className="flex flex-col gap-2 p-2">
            <div className="text-zinc-400 text-xs font-normal">
                {children || <p>The page you are looking for does not exist.</p>}
            </div>
            <p className="flex items-center gap-2 flex-wrap">
                <Button
                    type="button"
                    colorScheme="success"
                    size="sm"
                    className="uppercase font-bold text-xs"
                    onClick={() => window.history.back()}
                >
                    Go back
                </Button>
                <Link
                    to="/"
                    className="bg-accent text-white px-2.5 py-1 rounded-none uppercase font-bold text-xs shadow-sm"
                >
                    Start Over
                </Link>
            </p>
        </div>
    );
}
