import { Button, Input } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { type FormEvent, useState } from 'react';
import { compileStrategyFn } from '~/features/recipes/builder/compiler-api';
import type { PushStrategy } from '~/features/recipes/types';
import { type Described, interpretReply } from '../lib/describe';

export interface DescribeLineProps {
    onCompiled: (strategy: PushStrategy, summary: string, fallback: boolean) => void;
    onFailed?: (reason: string) => void;
    isAuthenticated: boolean;
    disabled?: boolean;
}

/**
 * One place where the network call and its failure are turned into copy, so the
 * handler stays a short sequence of state updates.
 */
async function readIdea(
    text: string,
): Promise<{ outcome: Described | null; error: string | null }> {
    try {
        const reply = await compileStrategyFn({
            data: { messages: [{ role: 'user', content: text }] },
        });
        return { outcome: interpretReply(reply), error: null };
    } catch (error) {
        return {
            outcome: null,
            error: error instanceof Error ? error.message : 'Could not read that idea.',
        };
    }
}

/**
 * "Describe it" is a convenience beside the blocks, not a second product: it
 * replaces the draft when it succeeds, and says so when it degraded to a starter.
 */
export function DescribeLine({
    onCompiled,
    onFailed,
    isAuthenticated,
    disabled = false,
}: DescribeLineProps) {
    const [idea, setIdea] = useState('');
    const [busy, setBusy] = useState(false);
    const [note, setNote] = useState<string | null>(null);

    const apply = ({ outcome, error }: { outcome: Described | null; error: string | null }) => {
        if (error) {
            setNote(/unauthorized|sign in/i.test(error) ? 'Sign in to describe a bot.' : error);
            onFailed?.(error);
            return;
        }
        if (!outcome) return;
        setNote(outcome.note);
        if (outcome.failed) onFailed?.(outcome.failed);
        if (!outcome.compiled) return;
        const { strategy, summary, fallback } = outcome.compiled;
        onCompiled(strategy, summary, fallback);
    };

    const submit = async (event: FormEvent) => {
        event.preventDefault();
        const text = idea.trim();
        if (!text || busy || disabled) return;
        setBusy(true);
        setNote(null);
        apply(await readIdea(text));
        setBusy(false);
    };

    return (
        <form className="flex flex-col gap-2 min-w-0" onSubmit={submit}>
            <div className="flex flex-wrap items-stretch gap-2">
                <div className="flex-1 basis-72 min-w-0">
                    <Input
                        aria-label="Describe your bot in one line"
                        placeholder="Buy chipmakers when AI capex news turns positive"
                        value={idea}
                        maxLength={280}
                        onChange={(event) => setIdea(event.target.value)}
                    />
                </div>
                <Button type="submit" variant="outline" size="md" disabled={busy || disabled}>
                    {busy ? 'Reading…' : 'Describe it'}
                </Button>
            </div>
            <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                {note ? (
                    <p className="text-xs font-normal text-voxel-muted" role="status">
                        {note}
                    </p>
                ) : null}
                <Link
                    to="/build"
                    search={{ idea: idea.trim() || undefined }}
                    className="text-xs font-normal text-voxel-muted hover:text-voxel-ink hover:underline whitespace-nowrap"
                >
                    {isAuthenticated ? 'Prefer a conversation?' : 'Build by conversation →'}
                </Link>
            </div>
        </form>
    );
}
