import { Button, Input } from '@llm-market-bench/ui-design-system';
import { type FormEvent, useState } from 'react';
import { submitRunRequestFn } from '../api/run-requests';

export interface RunRequestFormProps {
    isAuthenticated: boolean;
    defaultEmail?: string;
}

/** In flow, never a modal: the out-of-runs state asks for one row per day. */
export function RunRequestForm({ isAuthenticated, defaultEmail = '' }: RunRequestFormProps) {
    const [email, setEmail] = useState(defaultEmail);
    const [note, setNote] = useState('');
    const [state, setState] = useState<'idle' | 'busy' | 'sent' | 'already' | 'error'>('idle');
    const [error, setError] = useState<string | null>(null);

    const submit = async (event: FormEvent) => {
        event.preventDefault();
        if (state === 'busy' || state === 'sent' || state === 'already') return;
        setState('busy');
        setError(null);
        try {
            const result = await submitRunRequestFn({ data: { email, note } });
            if (result.kind === 'submitted') setState('sent');
            else if (result.kind === 'already') setState('already');
            else {
                setState('error');
                setError(result.needsAuth ? 'Sign in to ask for more runs.' : result.message);
            }
        } catch (caught) {
            setState('error');
            setError(caught instanceof Error ? caught.message : 'Could not send the request.');
        }
    };

    if (state === 'sent' || state === 'already') {
        return (
            <p className="voxel-trough p-3 text-xs font-normal text-voxel-ink" role="status">
                {state === 'sent'
                    ? 'Noted. You will get an email when more runs open up.'
                    : 'You already asked today — one request per day is enough.'}
            </p>
        );
    }

    return (
        <form className="voxel-trough flex flex-col gap-2 p-3" onSubmit={submit}>
            <p className="text-sm font-bold text-voxel-ink">Out of runs?</p>
            <p className="text-xs font-normal text-voxel-muted">
                Limits are two backtests a day. Ask for more and we will email you when the
                allowance grows.
            </p>
            <div className="flex flex-wrap gap-2">
                <div className="flex-1 basis-64 min-w-0">
                    <Input
                        aria-label="Email for the request"
                        placeholder="you@example.com"
                        value={email}
                        maxLength={200}
                        onChange={(event) => setEmail(event.target.value)}
                    />
                </div>
                <Button type="submit" variant="outline" size="md" disabled={state === 'busy'}>
                    {state === 'busy' ? 'Sending…' : 'Ask for more runs'}
                </Button>
            </div>
            <div className="flex-1 min-w-0">
                <Input
                    aria-label="What would you run"
                    placeholder="Optional: what would you run with one more?"
                    value={note}
                    maxLength={280}
                    onChange={(event) => setNote(event.target.value)}
                />
            </div>
            {error ? (
                <p className="text-xs font-normal text-danger" role="alert">
                    {error}
                </p>
            ) : null}
            {!isAuthenticated ? (
                <p className="text-xs font-normal text-voxel-muted">
                    Sign in first and the request is tied to your account.
                </p>
            ) : null}
        </form>
    );
}
