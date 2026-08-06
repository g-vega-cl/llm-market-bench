import type { GeneratedNewsletter } from '@llm-market-bench/database';
import { getSupabaseServerClient } from '~/lib/supabase';
import { formatEasternDate, formatEasternShortTime } from '~/utils/date';

export type FormattedGeneratedNewsletter = GeneratedNewsletter & {
    formattedDate: string;
    displayTime: string;
};

export async function fetchGeneratedNewsletters(
    limit: number = 20,
    sessionFilter?: 'open' | 'close' | 'all',
): Promise<FormattedGeneratedNewsletter[]> {
    const supabase = getSupabaseServerClient();

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

    return (data || []).map((item) => {
        const formattedDate = formatEasternDate(item.created_at);
        const fallbackTime = formatEasternShortTime(item.created_at);

        return {
            ...item,
            formattedDate,
            displayTime: item.formatted_time || fallbackTime,
        };
    });
}
