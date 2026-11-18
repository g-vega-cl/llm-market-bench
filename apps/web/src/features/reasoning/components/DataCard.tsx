import { Badge } from '@llm-market-bench/ui-design-system';

// biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
export function DataCard({ item }: { item: Record<string, any> }) {
    if (typeof item !== 'object' || item === null) {
        return (
            <div className="p-3 border border-voxel-bevel-hi rounded-none bg-voxel-trough font-mono text-xs font-normal text-voxel-ink">
                {String(item)}
            </div>
        );
    }

    const entries = Object.entries(item);
    const longTextFields = entries.filter(
        ([k, v]) =>
            typeof v === 'string' &&
            (v.length > 60 || k.includes('reasoning') || k.includes('summary')),
    );
    const shortFields = entries.filter(([k, _v]) => !longTextFields.find(([lk]) => lk === k));

    return (
        <div className="p-5 rounded-none border border-voxel-bevel-hi bg-voxel-surface shadow-sm hover:border-accent/40 transition-all duration-300 flex flex-col gap-6">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-4 items-stretch">
                {shortFields.map(([k, v]) => (
                    <div key={k} className="flex flex-col gap-1">
                        <h6 className="text-sm font-bold uppercase tracking-wider text-voxel-muted m-0">
                            {k.replace(/_/g, ' ')}
                        </h6>
                        <div className="text-sm font-bold text-voxel-ink break-words">
                            {typeof v === 'boolean' ? (
                                <Badge
                                    variant="soft"
                                    colorScheme={v ? 'success' : 'danger'}
                                    size="sm"
                                >
                                    {v ? 'YES' : 'NO'}
                                </Badge>
                            ) : (
                                String(v)
                            )}
                        </div>
                    </div>
                ))}
            </div>
            {longTextFields.length > 0 && (
                <div className="flex flex-col gap-4 pt-4 border-t border-voxel-bevel-lo">
                    {longTextFields.map(([k, v]) => (
                        <div key={k} className="flex flex-col gap-2">
                            <h6 className="text-sm font-bold uppercase tracking-wider text-voxel-muted m-0">
                                {k.replace(/_/g, ' ')}
                            </h6>
                            <div className="text-xs font-normal leading-relaxed text-voxel-ink whitespace-pre-wrap bg-voxel-trough p-3 rounded-none border border-voxel-bevel-hi">
                                {String(v)}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
