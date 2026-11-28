import { Button } from '@llm-market-bench/ui-design-system';
import type { KeyboardEvent, RefObject } from 'react';
import { DataCoverageNote } from '../components/DataCoverageNote';
import { BuilderActivePrompt, BuilderMessageHistory } from './BuilderConversation';
import { MAX_TURN_CHARS } from './compiler';
import type { BuilderChat } from './use-builder-chat';

const STARTER_IDEA_CHIPS = [
    {
        label: 'AI Capex Chips',
        prompt: 'Buy profitable semiconductor leaders on AI data-center capex news with RSI under 65 and positive MACD.',
    },
    {
        label: 'Earnings Drift',
        prompt: 'Trade post-earnings drift on profitable tech stocks that beat EPS and raised guidance without already spiking over 8%.',
    },
    {
        label: 'Quality Pullback',
        prompt: 'Buy high-ROE cash-generative companies pulling back below VWAP with RSI under 40.',
    },
    {
        label: 'Contrarian Fear',
        prompt: 'Buy oversold large-cap leaders when market sentiment is fearful and exit into euphoria.',
    },
] as const;

export function BuilderErrorBanner({
    error,
    isCompiling,
    onRetry,
    onUseTemplate,
}: {
    error: string;
    isCompiling: boolean;
    onRetry: () => void;
    onUseTemplate: () => void;
}) {
    return (
        <div
            role="alert"
            className="voxel-trough bg-voxel-trough flex flex-wrap items-center justify-between gap-2 p-3 min-w-0"
        >
            <p className="text-xs font-normal text-danger min-w-0 break-words">{error}</p>
            <div className="flex flex-wrap items-center gap-2 shrink-0 min-w-0">
                <Button
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    onClick={onRetry}
                    disabled={isCompiling}
                >
                    Try again
                </Button>
                <Button
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    onClick={onUseTemplate}
                    disabled={isCompiling}
                >
                    Use closest template
                </Button>
            </div>
        </div>
    );
}

function BuilderStarterChips({
    disabled,
    onSelect,
}: {
    disabled: boolean;
    onSelect: (prompt: string) => void;
}) {
    return (
        <div
            data-testid="builder-starter-chips"
            className="voxel-trough bg-voxel-trough rounded-none p-2 flex flex-col gap-2 min-w-0"
        >
            <span className="text-xs font-normal text-voxel-muted">
                Start with a template idea or write your own above:
            </span>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,7.5rem),1fr))] gap-2 min-w-0">
                {STARTER_IDEA_CHIPS.map((chip) => (
                    <Button
                        key={chip.label}
                        type="button"
                        size="sm"
                        variant="outline"
                        colorScheme="neutral"
                        disabled={disabled}
                        onClick={() => onSelect(chip.prompt)}
                    >
                        {chip.label}
                    </Button>
                ))}
            </div>
        </div>
    );
}

export interface BuilderDescribeStepProps {
    chat: BuilderChat;
    userId: string | null;
    isInitialStep: boolean;
    hintId: string;
    textareaRef: RefObject<HTMLTextAreaElement | null>;
    onFocusTextarea: () => void;
    onSelectChip: (prompt: string) => void;
}

/**
 * Step 1 of `/build`: keeps active prompts, the strategy textarea, and the
 * primary CTA front and center above starter chips and earlier history.
 */
export function BuilderDescribeStep({
    chat,
    userId,
    isInitialStep,
    hintId,
    textareaRef,
    onFocusTextarea,
    onSelectChip,
}: BuilderDescribeStepProps) {
    const handleTextareaKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
            event.preventDefault();
            if (chat.draft.trim() && !chat.isCompiling) {
                void chat.send(chat.draft);
            }
        }
    };

    return (
        <>
            {chat.error ? (
                <BuilderErrorBanner
                    error={chat.error}
                    isCompiling={chat.isCompiling}
                    onRetry={chat.retry}
                    onUseTemplate={chat.useTemplate}
                />
            ) : null}

            <BuilderActivePrompt
                messages={chat.messages}
                reply={chat.reply}
                pendingIdea={chat.pendingIdea}
                isSignedIn={Boolean(userId)}
                isCompiling={chat.isCompiling}
                hasError={Boolean(chat.error)}
                onSend={(text) => void chat.send(text)}
            />

            {!chat.isCompiling ? (
                <form
                    className="flex flex-col gap-3 min-w-0"
                    onSubmit={(event) => {
                        event.preventDefault();
                        void chat.send(chat.draft);
                    }}
                >
                    <div className="voxel-trough bg-voxel-trough rounded-none flex w-full p-3 transition-colors focus-within:ring-2 focus-within:ring-accent/40">
                        <textarea
                            ref={textareaRef}
                            rows={3}
                            aria-label="Describe your trading bot"
                            aria-describedby={hintId}
                            placeholder="Describe what your bot should trade and when to enter or exit..."
                            value={chat.draft}
                            onChange={(event) => chat.setDraft(event.target.value)}
                            onKeyDown={handleTextareaKeyDown}
                            onFocus={onFocusTextarea}
                            maxLength={MAX_TURN_CHARS}
                            className="w-full min-h-[clamp(3.5rem,7vw,4.5rem)] max-h-60 resize-none overflow-y-auto bg-transparent text-xs font-normal leading-relaxed text-voxel-ink placeholder:text-voxel-muted focus:outline-none disabled:opacity-50"
                        />
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-4 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 min-w-0">
                            <span
                                id={hintId}
                                className="text-xs font-normal text-voxel-muted min-w-0"
                            >
                                {`${String(chat.draft.length)} / ${String(MAX_TURN_CHARS)} · Ctrl/⌘+Enter to submit`}
                            </span>
                            {chat.draft.length > 0 ? (
                                <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    colorScheme="neutral"
                                    onClick={() => {
                                        chat.setDraft('');
                                        textareaRef.current?.focus();
                                    }}
                                >
                                    Clear
                                </Button>
                            ) : null}
                        </div>
                        <Button
                            type="submit"
                            variant="solid"
                            size="md"
                            colorScheme="accent"
                            className="voxel-btn--hero"
                            disabled={!chat.draft.trim()}
                        >
                            {isInitialStep ? 'Continue to Alignment →' : 'Send Answer →'}
                        </Button>
                    </div>
                    {!userId && !chat.pendingIdea ? (
                        <p className="text-xs font-normal text-voxel-muted leading-relaxed">
                            Next step asks for a free Google sign-in to prevent AI compile abuse and
                            save your bot &amp; paper backtests (15 tokens a week, no card). Your
                            draft stays saved in this browser and returns right here afterward.
                        </p>
                    ) : null}
                </form>
            ) : null}

            {isInitialStep && !chat.pendingIdea ? (
                <BuilderStarterChips disabled={chat.isCompiling} onSelect={onSelectChip} />
            ) : null}

            {isInitialStep && !chat.pendingIdea ? <DataCoverageNote /> : null}

            <BuilderMessageHistory
                messages={chat.messages}
                messageIds={chat.messageIds}
                reply={chat.reply}
                isCompiling={chat.isCompiling}
                hasError={Boolean(chat.error)}
            />
        </>
    );
}
