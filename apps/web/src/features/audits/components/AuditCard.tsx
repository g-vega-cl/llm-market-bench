import { Badge, Button, Card } from '@llm-market-bench/ui-design-system';
import * as React from 'react';

interface AuditCardProps {
    audit: {
        id: string;
        title: string;
        description: string;
        severity: string;
        audit_type: string;
        suggestion: string | null;
        created_at: string | null;
    };
}

const typeLabels: Record<string, string> = {
    DB_ANOMALY: 'DB Anomaly',
    DATA_QUALITY: 'Data Quality',
    CODE_ERROR: 'Code Error',
    SYSTEM_LOG: 'System Log',
    IMPROVEMENT: 'Improvement',
};

export function AuditCard({ audit }: AuditCardProps) {
    const [expanded, setExpanded] = React.useState(false);

    return (
        <Card variant="default" padding="md">
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                        <Badge variant="soft" size="sm">
                            {audit.severity}
                        </Badge>
                        <span className="text-xs text-voxel-muted uppercase tracking-wider">
                            {typeLabels[audit.audit_type] || audit.audit_type}
                        </span>
                        {audit.created_at && (
                            <span className="text-xs text-voxel-muted">
                                {new Date(audit.created_at).toLocaleDateString('en-US', {
                                    timeZone: 'America/New_York',
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric',
                                })}
                            </span>
                        )}
                    </div>
                    <h3 className="text-sm font-bold text-voxel-ink mb-2">{audit.title}</h3>
                    <p className="text-voxel-muted text-xs font-normal">{audit.description}</p>
                </div>
            </div>

            {audit.suggestion && (
                <div className="mt-4 pt-4 border-t border-voxel-bevel-hi">
                    <Button
                        type="button"
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        onClick={() => setExpanded(!expanded)}
                    >
                        {expanded ? 'Hide suggestion' : 'Show suggestion'}
                    </Button>
                    {expanded && (
                        <div className="mt-3 p-4 bg-zinc-800/50 rounded-none text-xs font-normal text-zinc-300 font-mono whitespace-pre-wrap">
                            {typeof audit.suggestion === 'string' &&
                            audit.suggestion.startsWith('[')
                                ? JSON.stringify(JSON.parse(audit.suggestion), null, 2)
                                : audit.suggestion}
                        </div>
                    )}
                </div>
            )}
        </Card>
    );
}
