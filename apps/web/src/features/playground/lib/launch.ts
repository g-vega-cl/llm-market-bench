import type { StrategyStage } from '~/features/recipes/types';
import { launchRecipeFn } from '../api/launch-recipe';
import { toStrategy } from './blocks';
import { describeStage } from './describe-stage';
import type { LaunchResult } from './launch-result';

/**
 * One place where a draft becomes a request. Errors are returned as an `error`
 * result rather than thrown, so the strip can always render something true.
 */
export async function launchDraft(
    stage: StrategyStage,
    name: string,
    live: boolean,
): Promise<LaunchResult> {
    const graph = toStrategy(stage, name, describeStage(stage));
    try {
        return await launchRecipeFn({
            data: {
                graph,
                live,
                name: graph.name,
                description: graph.description ?? '',
            },
        });
    } catch (error) {
        return {
            kind: 'error',
            retryable: true,
            message: error instanceof Error ? error.message : 'The run request failed.',
        };
    }
}
