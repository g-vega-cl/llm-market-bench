import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { buildStagePromptPreview } from '../prompt-builder';
import type { PreviewState, StrategyStage } from '../types';

interface PromptVisualizerProps {
    stage: StrategyStage;
    stageIndex: number;
    previewState: PreviewState;
    onPreviewLiveData: () => void;
}

export function PromptVisualizer({
    stage,
    stageIndex,
    previewState,
    onPreviewLiveData,
}: PromptVisualizerProps) {
    const hydratedMap = previewState.status === 'hydrated' ? previewState.hydratedByBlockId : {};
    const promptText = buildStagePromptPreview(stage, hydratedMap, stageIndex);

    return (
        <div className="flex flex-col gap-2 border border-border bg-boxel-surface p-4 rounded-none">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-foreground">
                        Prompt Visualizer — {stage.title}
                    </span>
                    <Badge variant="outline" size="sm">
                        {previewState.status === 'hydrated'
                            ? 'Live DB Hydrated'
                            : 'Template Preview'}
                    </Badge>
                </div>
                <Button
                    size="sm"
                    variant="outline"
                    onClick={onPreviewLiveData}
                    disabled={previewState.status === 'loading'}
                >
                    {previewState.status === 'loading' ? 'Fetching...' : 'Preview Live Data'}
                </Button>
            </div>

            {previewState.status === 'error' && (
                <div className="border border-destructive bg-boxel-canvas p-2 text-xs font-normal text-destructive rounded-none">
                    {previewState.message}
                </div>
            )}

            <pre className="voxel-trough border border-border bg-boxel-canvas p-3 text-xs font-mono font-normal text-foreground whitespace-pre-wrap break-words rounded-none">
                {promptText}
            </pre>
        </div>
    );
}
