import { Button, SectionHeading } from '@llm-market-bench/ui-design-system';
import { type KeyboardEvent, useRef } from 'react';
import { PromptVisualizer } from '../components/PromptVisualizer';
import { StageBuilder } from '../components/StageBuilder';
import type { PreviewState, StrategyStage } from '../types';

export type WorkspaceTab = 'blocks' | 'prompt';

export interface CompiledBotBlueprintSectionProps {
    activeTab: WorkspaceTab;
    onSelectTab: (tab: WorkspaceTab) => void;
    stage: StrategyStage;
    preview: PreviewState;
    onStageChange: (updated: StrategyStage) => void;
    onPreviewLiveData: () => void;
}

function resolveNextTab(key: string, activeTab: WorkspaceTab): WorkspaceTab | null {
    if (key === 'ArrowRight' || key === 'ArrowLeft') {
        return activeTab === 'blocks' ? 'prompt' : 'blocks';
    }
    if (key === 'Home') return 'blocks';
    if (key === 'End') return 'prompt';
    return null;
}

/**
 * Lower calm workspace block for Step 2 of `/build`, replacing the old
 * collapsible drawers with a WAI-ARIA segmented tab bar (`Blocks & Tools`
 * active by default, switching flatly to `Prompt Preview`).
 */
export function CompiledBotBlueprintSection({
    activeTab,
    onSelectTab,
    stage,
    preview,
    onStageChange,
    onPreviewLiveData,
}: CompiledBotBlueprintSectionProps) {
    const blocksTabRef = useRef<HTMLButtonElement>(null);
    const promptTabRef = useRef<HTMLButtonElement>(null);

    const handleTabKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
        const nextTab = resolveNextTab(event.key, activeTab);
        if (!nextTab) return;
        event.preventDefault();
        onSelectTab(nextTab);
        const target = nextTab === 'blocks' ? blocksTabRef.current : promptTabRef.current;
        target?.focus();
    };

    return (
        <section
            data-testid="compiled-bot-workspace-section"
            className="mx-auto w-full max-w-7xl px-6 py-6 flex flex-col gap-4 min-w-0"
        >
            <div className="flex flex-wrap items-center justify-between gap-4 min-w-0">
                <SectionHeading className="text-sm">Strategy blueprint</SectionHeading>
                <div
                    role="tablist"
                    aria-label="Strategy blueprint views"
                    onKeyDown={handleTabKeyDown}
                    className="voxel-trough bg-voxel-trough inline-flex flex-wrap items-center gap-2 p-2 rounded-none"
                >
                    <Button
                        ref={blocksTabRef}
                        id="tab-blocks"
                        type="button"
                        role="tab"
                        aria-selected={activeTab === 'blocks'}
                        aria-controls="panel-blocks"
                        tabIndex={activeTab === 'blocks' ? 0 : -1}
                        size="sm"
                        variant={activeTab === 'blocks' ? 'solid' : 'outline'}
                        colorScheme={activeTab === 'blocks' ? 'accent' : 'neutral'}
                        onClick={() => onSelectTab('blocks')}
                    >
                        Blocks &amp; Tools
                    </Button>
                    <Button
                        ref={promptTabRef}
                        id="tab-prompt"
                        type="button"
                        role="tab"
                        aria-selected={activeTab === 'prompt'}
                        aria-controls="panel-prompt"
                        tabIndex={activeTab === 'prompt' ? 0 : -1}
                        size="sm"
                        variant={activeTab === 'prompt' ? 'solid' : 'outline'}
                        colorScheme={activeTab === 'prompt' ? 'accent' : 'neutral'}
                        onClick={() => onSelectTab('prompt')}
                    >
                        Prompt Preview
                    </Button>
                </div>
            </div>

            <div
                id={activeTab === 'blocks' ? 'panel-blocks' : 'panel-prompt'}
                role="tabpanel"
                aria-labelledby={activeTab === 'blocks' ? 'tab-blocks' : 'tab-prompt'}
                className="min-w-0"
            >
                {activeTab === 'blocks' ? (
                    <StageBuilder stage={stage} onChange={onStageChange} />
                ) : (
                    <PromptVisualizer
                        stage={stage}
                        previewState={preview}
                        onPreviewLiveData={onPreviewLiveData}
                    />
                )}
            </div>
        </section>
    );
}
