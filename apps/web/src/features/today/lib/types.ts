export interface CauseAndEffectEntry {
    id: string;
    event: { content?: string };
    analysis: string;
    market_outcome: string;
    confidence: number;
    tags?: string[];
    created_at: string;
}
