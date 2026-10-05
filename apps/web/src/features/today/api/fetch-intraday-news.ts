import type { IntradayMarketNews } from '@llm-market-bench/database';
import { getSupabaseServerClient } from '~/lib/supabase';
import { formatEasternDate, formatEasternShortTime } from '~/utils/date';

export type FormattedIntradayNews = IntradayMarketNews & {
    formattedTime: string;
    formattedDate: string;
};

export async function fetchIntradayNews(limit = 20): Promise<FormattedIntradayNews[]> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase
        .from('intraday_market_news')
        .select('*')
        .order('event_timestamp', { ascending: false })
        .limit(limit);

    if (error) {
        console.warn('Error fetching intraday market news:', error);
        return [];
    }

    return (data || []).map((item) => ({
        ...item,
        formattedTime: formatEasternShortTime(item.event_timestamp),
        formattedDate: formatEasternDate(item.event_timestamp),
    }));
}
