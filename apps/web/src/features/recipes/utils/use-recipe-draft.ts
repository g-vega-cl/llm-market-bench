import { useCallback, useRef, useState } from 'react';
import type { RecipeSaveState } from '../components/RecipeNameField';
import type { PushStrategy, StrategyRecipeRecord, StrategyStage } from '../types';

type PersistFn = (strategy: PushStrategy) => Promise<StrategyRecipeRecord>;

/** Thrown so run/schedule callers can tell a failed save from a failed run. */
export class RecipeSaveError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'RecipeSaveError';
    }
}

export interface RecipeDraft {
    strategy: PushStrategy;
    isDirty: boolean;
    isSaving: boolean;
    saveState: RecipeSaveState;
    saveError: string | null;
    setName: (name: string) => void;
    setStage: (stage: StrategyStage) => void;
    resetTo: (template: PushStrategy) => void;
    save: (persist: PersistFn) => Promise<StrategyRecipeRecord>;
}

interface InFlightSave {
    promise: Promise<StrategyRecipeRecord>;
    revision: number;
    generation: number;
}

/**
 * Draft + explicit-save state machine for the recipe studio.
 *
 * Three invariants keep edits from being lost or misattributed:
 *
 * 1. `draftRev` advances on every edit. A response that lands against a newer
 *    revision adopts the row id but never overwrites the local draft.
 * 2. `isSaving` is cleared only when the request settles — never by an edit —
 *    so run/schedule stay disabled for the whole flight.
 * 3. `generation` advances when the draft is replaced (template selection). A
 *    response from an older generation is ignored entirely, so it cannot stamp
 *    the old row id onto a fresh template.
 *
 * A save requested at an advanced revision joins the in-flight request and then
 * persists the current draft, so a queued run always gets the edited snapshot.
 */
export function useRecipeDraft(
    initialStrategy: PushStrategy,
    initialPersistedName: string | null,
): RecipeDraft {
    const [strategy, setStrategy] = useState<PushStrategy>(initialStrategy);
    const [persistedName, setPersistedName] = useState<string | null>(initialPersistedName);
    const [isGraphDirty, setIsGraphDirty] = useState(false);
    const [saveState, setSaveState] = useState<RecipeSaveState>('idle');
    const [saveError, setSaveError] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);

    const strategyRef = useRef(strategy);
    strategyRef.current = strategy;

    const draftRev = useRef(0);
    const generation = useRef(0);
    const inFlight = useRef<InFlightSave | null>(null);

    const setName = useCallback((name: string) => {
        draftRev.current += 1;
        setStrategy((prev) => ({ ...prev, name }));
        setSaveState('idle');
    }, []);

    const setStage = useCallback((stage: StrategyStage) => {
        draftRev.current += 1;
        setStrategy((prev) => ({ ...prev, stages: [stage] }));
        setIsGraphDirty(true);
        setSaveState('idle');
    }, []);

    const resetTo = useCallback((template: PushStrategy) => {
        draftRev.current += 1;
        generation.current += 1;
        const [stage] = template.stages;
        setStrategy({
            ...template,
            id: undefined,
            stages: [{ ...stage, blocks: [...stage.blocks] }],
        });
        setPersistedName(null);
        setIsGraphDirty(false);
        setSaveState('idle');
        setSaveError(null);
    }, []);

    const runPersist = useCallback((persist: PersistFn): Promise<StrategyRecipeRecord> => {
        const revision = draftRev.current;
        const draftGeneration = generation.current;
        const snapshot = strategyRef.current;

        setIsSaving(true);
        setSaveState('saving');
        setSaveError(null);

        const request = persist(snapshot)
            .then((saved) => {
                const sameGeneration = draftGeneration === generation.current;
                const unchanged = sameGeneration && revision === draftRev.current;
                if (sameGeneration) {
                    setStrategy((prev) => ({
                        ...prev,
                        id: saved.id,
                        name: unchanged ? (saved.name ?? prev.name) : prev.name,
                    }));
                    setPersistedName(saved.name ?? snapshot.name);
                    setIsGraphDirty((prev) => (unchanged ? false : prev));
                }
                setSaveState(unchanged ? 'saved' : 'idle');
                setSaveError(null);
                return saved;
            })
            .catch((err: unknown) => {
                const message = err instanceof Error ? err.message : 'Failed to save recipe';
                setSaveState('error');
                setSaveError(message);
                throw new RecipeSaveError(message);
            })
            .finally(() => {
                inFlight.current = null;
                setIsSaving(false);
            });

        inFlight.current = { promise: request, revision, generation: draftGeneration };
        return request;
    }, []);

    const save = useCallback(
        (persist: PersistFn): Promise<StrategyRecipeRecord> => {
            const active = inFlight.current;
            if (!active) return runPersist(persist);

            // Same draft: share the request. Newer draft: persist it afterwards,
            // so a run never enqueues the pre-edit graph.
            if (active.revision === draftRev.current) return active.promise;

            const chained = active.promise.catch(() => undefined).then(() => runPersist(persist));
            inFlight.current = {
                promise: chained,
                revision: draftRev.current,
                generation: generation.current,
            };
            return chained;
        },
        [runPersist],
    );

    return {
        strategy,
        isDirty: strategy.name !== persistedName || isGraphDirty,
        isSaving,
        saveState,
        saveError,
        setName,
        setStage,
        resetTo,
        save,
    };
}
