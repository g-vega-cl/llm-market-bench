import type { CompilerReply } from '~/features/recipes/builder/compiler';
import type { PushStrategy } from '~/features/recipes/types';

export interface Described {
    note: string;
    compiled?: { strategy: PushStrategy; summary: string; fallback: boolean };
    failed?: string;
}

/**
 * One reading of a compiler reply. A degraded answer says so instead of passing
 * a starter off as the visitor's idea.
 */
export function interpretReply(reply: CompilerReply): Described {
    if (reply.status === 'ok') {
        return {
            note: reply.fallback
                ? 'That idea could not be read, so a starter was loaded — edit it below.'
                : reply.summary,
            compiled: {
                strategy: reply.strategy,
                summary: reply.summary,
                fallback: Boolean(reply.fallback),
            },
        };
    }
    if (reply.status === 'question') return { note: reply.question };
    return {
        note: reply.closest
            ? `${reply.reason} Closest buildable version: ${reply.closest}`
            : reply.reason,
        failed: reply.reason,
    };
}
