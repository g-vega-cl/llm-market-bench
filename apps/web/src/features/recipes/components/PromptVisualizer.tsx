import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { buildStagePromptPreview } from '../prompt-builder';
import type { PreviewState, StrategyStage } from '../types';

interface PromptVisualizerProps {
    stage: StrategyStage;
    previewState: PreviewState;
    onPreviewLiveData: () => void;
}

export function PromptVisualizer({
    stage,
    previewState,
    onPreviewLiveData,
}: PromptVisualizerProps) {
    const hydratedMap = previewState.status === 'hydrated' ? previewState.hydratedByBlockId : {};
    const promptText = buildStagePromptPreview(stage, hydratedMap);

    return (
        <div className="flex flex-col gap-2 border border-voxel-bevel-hi bg-voxel-surface p-4 rounded-none">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-voxel-ink">Prompt Visualizer</span>
                    <Badge variant="soft" size="sm">
                        {previewState.status === 'hydrated'
                            ? 'Live DB Hydrated'
                            : 'Template Preview'}
                    </Badge>
                </div>
                <Button
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    onClick={onPreviewLiveData}
                    disabled={previewState.status === 'loading'}
                >
                    {previewState.status === 'loading' ? 'Fetching...' : 'Preview Live Data'}
                </Button>
            </div>

            {previewState.status === 'error' && (
                <div className="border border-danger bg-voxel-canvas p-2 text-xs font-normal text-danger rounded-none">
                    {previewState.message}
                </div>
            )}

            <pre className="voxel-trough border border-voxel-bevel-hi bg-voxel-canvas p-3 text-xs font-mono font-normal text-voxel-ink whitespace-pre-wrap break-words rounded-none">
                {promptText}
            </pre>
        </div>
    );
}
