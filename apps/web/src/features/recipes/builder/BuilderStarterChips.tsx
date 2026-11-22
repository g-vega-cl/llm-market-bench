import { Button } from '@llm-market-bench/ui-design-system';

export interface StarterIdea {
    label: string;
    prompt: string;
}

export const BUILDER_STARTER_IDEAS: StarterIdea[] = [
    {
        label: 'Momentum: AI Capex',
        prompt: 'Buy leading chipmakers when AI capex news is positive, exit on guidance cuts.',
    },
    {
        label: 'Earnings Beat',
        prompt: 'Buy S&P 500 stocks with strong EPS beats and raised guidance, hold for 5 days.',
    },
    {
        label: 'Contrarian Dip',
        prompt: 'Buy oversold quality tech when RSI drops below 32 and macro barometer stays neutral.',
    },
    {
        label: 'Defensive Hedge',
        prompt: 'Rotate into short treasuries and low-beta staples when VIX spikes and credit spreads widen.',
    },
];

export interface BuilderStarterChipsProps {
    onSelect: (prompt: string) => void;
    disabled?: boolean;
}

/**
 * Clickable starter-idea chips for /build's idle state. Clicking a chip
 * populates the prompt input (explicit over implicit) rather than auto-sending.
 */
export function BuilderStarterChips({ onSelect, disabled = false }: BuilderStarterChipsProps) {
    return (
        <div
            data-testid="builder-starter-chips"
            className="voxel-trough bg-voxel-trough rounded-none p-3 flex flex-col gap-2 min-w-0"
        >
            <span className="text-xs font-normal uppercase tracking-wider text-voxel-muted">
                Starter ideas (click to fill)
            </span>
            <div className="flex flex-wrap gap-2">
                {BUILDER_STARTER_IDEAS.map((item) => (
                    <Button
                        key={item.label}
                        type="button"
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        disabled={disabled}
                        onClick={() => onSelect(item.prompt)}
                    >
                        {item.label}
                    </Button>
                ))}
            </div>
        </div>
    );
}
