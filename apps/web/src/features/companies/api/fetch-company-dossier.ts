import { getDbServerClient } from '~/lib/db';
import { formatEasternDate } from '~/utils/date';

export interface CompanyResearchReport {
    id: string;
    ticker: string;
    company_name: string;
    sector: string | null;
    is_sector_etf: boolean;
    entity_type: string;
    session: string;
    date: string;
    formatted_date: string;
    verdict: 'bullish' | 'bearish' | 'neutral';
    conviction_score: number;
    risk_reward_score: number | null;
    target_horizon: string;
    spot_price_at_report: number | null;
    forward_5d_return: number | null;
    forward_20d_return: number | null;
    valuation_summary: string | null;
    buffett_moat_analysis: Record<string, string | number | boolean | null> | null;
    options_sentiment_summary: string | null;
    catalyst_context: string | null;
    falsification_triggers: string[];
    full_report_markdown: string;
    created_at: string;
}

export interface CompanyDossierData {
    ticker: string;
    latestReport: CompanyResearchReport | null;
    pastReports: CompanyResearchReport[];
    mentionCount: number;
}

export async function fetchCompanyDossier(rawTicker: string): Promise<CompanyDossierData> {
    const ticker = rawTicker.trim().toUpperCase();
    const supabase = getDbServerClient();

    const { data: reports, error } = await supabase
        .from('company_research_reports')
        .select('*')
        .eq('ticker', ticker)
        .order('date', { ascending: false })
        .order('created_at', { ascending: false });

    if (error) {
        console.error(`Error fetching research dossier for ${ticker}:`, error);
        return {
            ticker,
            latestReport: null,
            pastReports: [],
            mentionCount: 0,
        };
    }

    const { count } = await supabase
        .from('newsletter_company_mentions')
        .select('*', { count: 'exact', head: true })
        .eq('ticker', ticker);

    const formattedReports: CompanyResearchReport[] = (reports || []).map((r) => ({
        id: r.id,
        ticker: r.ticker,
        company_name: r.company_name || r.ticker,
        sector: r.sector,
        is_sector_etf: Boolean(r.is_sector_etf),
        entity_type: r.entity_type || 'stock',
        session: r.session,
        date: r.date,
        formatted_date: formatEasternDate(r.date),
        verdict: r.verdict as 'bullish' | 'bearish' | 'neutral',
        conviction_score: r.conviction_score,
        risk_reward_score: r.risk_reward_score,
        target_horizon: r.target_horizon,
        spot_price_at_report: r.spot_price_at_report,
        forward_5d_return: r.forward_5d_return,
        forward_20d_return: r.forward_20d_return,
        valuation_summary: r.valuation_summary,
        buffett_moat_analysis: r.buffett_moat_analysis || null,
        options_sentiment_summary: r.options_sentiment_summary,
        catalyst_context: r.catalyst_context,
        falsification_triggers: Array.isArray(r.falsification_triggers)
            ? r.falsification_triggers
            : [],
        full_report_markdown: r.full_report_markdown,
        created_at: r.created_at,
    }));

    const latest = formattedReports.length > 0 ? formattedReports[0] : null;
    const past = formattedReports.length > 1 ? formattedReports.slice(1) : [];

    return {
        ticker,
        latestReport: latest,
        pastReports: past,
        mentionCount: Math.max(formattedReports.length, count || 0),
    };
}
