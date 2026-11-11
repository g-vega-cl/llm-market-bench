import type { GeneratedNewsletter } from '@llm-market-bench/database';
import { getDbServerClient } from '~/lib/db';
import { formatEasternDate, formatEasternShortTime } from '~/utils/date';

export interface CompanySpotlightSummary {
    id: string;
    ticker: string;
    company_name: string;
    sector: string | null;
    is_sector_etf: boolean;
    entity_type: string;
    verdict: 'bullish' | 'bearish' | 'neutral';
    conviction_score: number;
    risk_reward_score: number | null;
    target_horizon: string;
    spot_price_at_report: number | null;
    catalyst_context: string | null;
    valuation_summary: string | null;
}

export type FormattedGeneratedNewsletter = GeneratedNewsletter & {
    formattedDate: string;
    displayTime: string;
    spotlight_companies?: CompanySpotlightSummary[];
};

function transformReportToSpotlight(
    report: CompanySpotlightSummary | null,
): CompanySpotlightSummary | null {
    if (!report?.ticker) return null;
    return {
        id: report.id,
        ticker: report.ticker,
        company_name: report.company_name || report.ticker,
        sector: report.sector || null,
        is_sector_etf: Boolean(report.is_sector_etf),
        entity_type: report.entity_type || 'stock',
        verdict: (report.verdict || 'neutral') as 'bullish' | 'bearish' | 'neutral',
        conviction_score: report.conviction_score || 50,
        risk_reward_score: report.risk_reward_score ?? null,
        target_horizon: report.target_horizon || '1-3 months',
        spot_price_at_report: report.spot_price_at_report ?? null,
        catalyst_context: report.catalyst_context ?? null,
        valuation_summary: report.valuation_summary ?? null,
    };
}

// biome-ignore lint/suspicious/noExplicitAny: Supabase server client
async function fetchMentionsMap(supabase: any, newsletterIds: string[]) {
    const mentionsByNewsletter: Record<string, CompanySpotlightSummary[]> = {};
    if (newsletterIds.length === 0) return mentionsByNewsletter;

    try {
        const { data: mentions, error: mentionsErr } = await supabase
            .from('newsletter_company_mentions')
            .select(`
                newsletter_id,
                ticker,
                research_report_id,
                company_research_reports (
                    id,
                    ticker,
                    company_name,
                    sector,
                    is_sector_etf,
                    entity_type,
                    verdict,
                    conviction_score,
                    risk_reward_score,
                    target_horizon,
                    spot_price_at_report,
                    catalyst_context,
                    valuation_summary
                )
            `)
            .in('newsletter_id', newsletterIds);

        if (!mentionsErr && mentions) {
            for (const m of mentions) {
                const spotlight = transformReportToSpotlight(
                    m.company_research_reports as unknown as CompanySpotlightSummary | null,
                );
                if (spotlight) {
                    if (!mentionsByNewsletter[m.newsletter_id]) {
                        mentionsByNewsletter[m.newsletter_id] = [];
                    }
                    mentionsByNewsletter[m.newsletter_id].push(spotlight);
                }
            }
        }
    } catch (e) {
        console.warn('Could not load company research mentions for newsletters:', e);
    }

    return mentionsByNewsletter;
}

export async function fetchGeneratedNewsletters(
    limit: number = 20,
    sessionFilter?: 'open' | 'close' | 'all',
): Promise<FormattedGeneratedNewsletter[]> {
    const supabase = getDbServerClient();

    let query = supabase
        .from('generated_newsletters')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(limit);

    if (sessionFilter && sessionFilter !== 'all') {
        query = query.eq('session', sessionFilter);
    }

    const { data, error } = await query;

    if (error) {
        console.error('Error fetching generated newsletters:', error);
        return [];
    }

    const newsletters = data || [];
    if (newsletters.length === 0) {
        return [];
    }

    const newsletterIds = newsletters.map((n) => n.id);
    const mentionsByNewsletter = await fetchMentionsMap(supabase, newsletterIds);

    return newsletters.map((item) => {
        const formattedDate = formatEasternDate(item.created_at);
        const fallbackTime = formatEasternShortTime(item.created_at);

        return {
            ...item,
            formattedDate,
            displayTime: item.formatted_time || fallbackTime,
            spotlight_companies: mentionsByNewsletter[item.id] || [],
        };
    });
}
