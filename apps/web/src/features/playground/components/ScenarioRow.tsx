import { Button } from '@llm-market-bench/ui-design-system';
import type { Scenario } from '../lib/scenarios';

export interface ScenarioRowProps {
    scenarios: Scenario[];
    activeId: string | null;
    onPick: (scenario: Scenario) => void;
}

/** Five starting points. Picking one replaces the draft, nothing else. */
export function ScenarioRow({ scenarios, activeId, onPick }: ScenarioRowProps) {
    const active = scenarios.find((scenario) => scenario.id === activeId) ?? null;
    return (
        <div className="flex flex-col gap-2 min-w-0">
            <span className="text-xs font-normal text-voxel-muted">
                Or start from a live strategy:
            </span>
            <ul className="flex flex-wrap gap-2">
                {scenarios.map((scenario) => (
                    <li key={scenario.id} className="min-w-0">
                        <Button
                            size="sm"
                            variant={scenario.id === activeId ? 'solid' : 'outline'}
                            colorScheme="neutral"
                            aria-pressed={scenario.id === activeId}
                            onClick={() => onPick(scenario)}
                        >
                            {scenario.label}
                        </Button>
                    </li>
                ))}
            </ul>
            {active ? <p className="text-xs font-normal text-voxel-muted">{active.blurb}</p> : null}
        </div>
    );
}
