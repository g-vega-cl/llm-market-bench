import { getDbServerClient } from '~/lib/db';
import { formatEasternDate } from '~/utils/date';

export interface CompanySummaryItem {
    ticker: string;
    company_name: string;
    sector: string | null;
    is_sector_etf: boolean;
    entity_type: string;
    latest_verdict: 'bullish' | 'bearish' | 'neutral';
    latest_conviction: number;
    latest_date: string;
    formatted_date: string;
    spot_price_at_report: number | null;
    mention_count: number;
}

export async function fetchCompaniesList(limit: number = 60): Promise<CompanySummaryItem[]> {
    const supabase = getDbServerClient();

    // Lean projected query: strictly exclude heavy markdown & text blobs (Principle 9)
    const { data: reports, error: reportErr } = await supabase
        .from('company_research_reports')
        .select(
            'ticker, company_name, sector, is_sector_etf, entity_type, verdict, conviction_score, date, spot_price_at_report',
        )
        .order('date', { ascending: false })
        .limit(limit);

    if (reportErr) {
        console.error('Error fetching company research reports:', reportErr);
        return [];
    }

    // Query mention counts per ticker
    const { data: mentions, error: mentionErr } = await supabase
        .from('newsletter_company_mentions')
        .select('ticker');

    const mentionCounts: Record<string, number> = {};
    if (!mentionErr && mentions) {
        for (const m of mentions) {
            mentionCounts[m.ticker] = (mentionCounts[m.ticker] || 0) + 1;
        }
    }

    // Deduplicate on ticker, keeping the most recent report for each company
    const dedupedMap = new Map<string, CompanySummaryItem>();

    for (const r of reports || []) {
        const ticker = r.ticker.toUpperCase();
        if (!dedupedMap.has(ticker)) {
            dedupedMap.set(ticker, {
                ticker,
                company_name: r.company_name || ticker,
                sector: r.sector,
                is_sector_etf: Boolean(r.is_sector_etf),
                entity_type: r.entity_type || 'stock',
                latest_verdict: r.verdict as 'bullish' | 'bearish' | 'neutral',
                latest_conviction: r.conviction_score || 50,
                latest_date: r.date,
                formatted_date: formatEasternDate(r.date),
                spot_price_at_report: r.spot_price_at_report,
                mention_count: Math.max(1, mentionCounts[ticker] || 1),
            });
        }
    }

    return Array.from(dedupedMap.values());
}
