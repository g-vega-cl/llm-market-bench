import { Button } from '@llm-market-bench/ui-design-system';

/**
 * Quiet public/private control on a bot card.
 *
 * Rendered through the `Button` primitive (the repo forbids ad-hoc button
 * elements in `apps/web`, and its contrast audit forbids recolouring a Button
 * from `className`), so the quiet treatment is geometry only: the outline is
 * made transparent, the voxel offset shadow is dropped, and the label sits at
 * 12px normal weight. It reads as the bot's state — "Public" / "Private" — and
 * flips that state on click; `aria-pressed` carries the state and the label
 * names the flip, so a screen reader never has to infer it from the visible
 * word. Deliberately low-emphasis: this is an opt-out, not a primary action.
 */
export function BotVisibilityToggle({
    name,
    isPublic,
    disabled,
    testId,
    onToggle,
}: {
    name: string;
    isPublic: boolean;
    disabled: boolean;
    testId?: string;
    onToggle: () => void;
}) {
    return (
        <Button
            variant="outline"
            colorScheme="neutral"
            size="sm"
            data-testid={testId}
            aria-pressed={isPublic}
            aria-label={`Bot visibility for ${name}`}
            disabled={disabled}
            onClick={onToggle}
            className="border-transparent! shadow-none! px-1 py-0.5 text-xs font-normal whitespace-nowrap"
        >
            {isPublic ? 'Public' : 'Private'}
        </Button>
    );
}
