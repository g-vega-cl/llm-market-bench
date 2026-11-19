import type { PushStrategy } from '../types';

export const DRAFT_STORAGE_KEY = 'recipe_draft:v1';
export const PENDING_BUILDER_KEY = 'recipe_builder_pending:v1';

export interface LocalDraft {
    strategy: PushStrategy;
    savedAt: string;
    source: 'builder' | 'studio';
}

function readJson<T>(key: string): T | null {
    if (typeof window === 'undefined') return null;
    try {
        const raw = window.localStorage.getItem(key);
        if (!raw) return null;
        return JSON.parse(raw) as T;
    } catch {
        return null;
    }
}

function writeJson(key: string, value: unknown): void {
    if (typeof window === 'undefined') return;
    try {
        window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
        // Storage full or disabled (private mode): the draft simply stays in memory.
    }
}

/** Keep the visitor's work in this browser until they sign in and run it. */
export function saveLocalDraft(
    strategy: PushStrategy,
    source: LocalDraft['source'] = 'studio',
): void {
    writeJson(DRAFT_STORAGE_KEY, {
        strategy,
        savedAt: new Date().toISOString(),
        source,
    } satisfies LocalDraft);
}

export function loadLocalDraft(): LocalDraft | null {
    const draft = readJson<LocalDraft>(DRAFT_STORAGE_KEY);
    if (!draft || typeof draft !== 'object' || !draft.strategy) return null;
    if (!Array.isArray(draft.strategy.stages) || draft.strategy.stages.length !== 1) return null;
    return draft;
}

export function clearLocalDraft(): void {
    if (typeof window === 'undefined') return;
    try {
        window.localStorage.removeItem(DRAFT_STORAGE_KEY);
    } catch {
        // Nothing to do: a failed clear must not block navigation.
    }
}

/**
 * An anonymous visitor's first builder message. It is stored before the login
 * redirect and replayed on return, so signing in never costs them their idea.
 */
export function savePendingIdea(idea: string): void {
    writeJson(PENDING_BUILDER_KEY, { idea, savedAt: new Date().toISOString() });
}

export function loadPendingIdea(): string | null {
    const pending = readJson<{ idea?: string }>(PENDING_BUILDER_KEY);
    const idea = pending?.idea?.trim();
    return idea ? idea : null;
}

export function clearPendingIdea(): void {
    if (typeof window === 'undefined') return;
    try {
        window.localStorage.removeItem(PENDING_BUILDER_KEY);
    } catch {
        // Ignore: the idea is advisory only.
    }
}
