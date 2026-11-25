import type {
    LeaderboardEntityType,
    LeaderboardPagePayload,
    LLMLeaderboardRow,
} from '@llm-market-bench/database';
import { getDbServerClient } from '~/lib/db';

export type LeaderboardCategory = 'all' | LeaderboardEntityType;
export type LeaderboardSortField =
    | 'composite_score'
    | 'return_pct'
    | 'win_rate'
    | 'consistency_score';
export type LeaderboardSortDir = 'asc' | 'desc';

export interface FetchLeaderboardPageParams {
    timeWindowDays: number | null;
    category?: LeaderboardCategory;
    sortBy?: LeaderboardSortField;
    sortDir?: LeaderboardSortDir;
    page?: number;
    pageSize?: number;
}

interface RawLeaderboardPageRow extends LLMLeaderboardRow {
    rank: number;
    total_count: number;
    all_count: number;
    llm_count: number;
    system_count: number;
    user_bot_count: number;
    is_podium: boolean;
    is_page_row: boolean;
}

function toLeaderboardRow(raw: RawLeaderboardPageRow): LLMLeaderboardRow {
    const {
        total_count: _totalCount,
        all_count: _allCount,
        llm_count: _llmCount,
        system_count: _systemCount,
        user_bot_count: _userBotCount,
        is_podium: _isPodium,
        is_page_row: _isPageRow,
        ...row
    } = raw;
    return row;
}

export async function fetchLeaderboard(
    timeWindowDays: number | null,
): Promise<LLMLeaderboardRow[]> {
    const supabase = getDbServerClient();
    const { data, error } = await supabase.rpc(
        'get_llm_leaderboard_metrics',
        { time_window_days: timeWindowDays },
        { get: true },
    );

    if (error) {
        console.error('Error in fetchLeaderboard:', error);
        throw error;
    }

    return (data || []) as LLMLeaderboardRow[];
}

export async function fetchLeaderboardPage({
    timeWindowDays,
    category = 'all',
    sortBy = 'composite_score',
    sortDir = 'desc',
    page = 1,
    pageSize = 10,
}: FetchLeaderboardPageParams): Promise<LeaderboardPagePayload> {
    const supabase = getDbServerClient();
    const safePage = Math.max(1, page);
    const offset = (safePage - 1) * pageSize;

    const { data, error } = await supabase.rpc(
        'get_leaderboard_page',
        {
            p_time_window_days: timeWindowDays,
            p_category: category,
            p_sort_by: sortBy,
            p_sort_dir: sortDir,
            p_limit: pageSize,
            p_offset: offset,
        },
        { get: true },
    );

    if (error) {
        console.error('Error in fetchLeaderboardPage:', error);
        throw error;
    }

    const rawRows = (data || []) as RawLeaderboardPageRow[];
    if (rawRows.length === 0) {
        return {
            rows: [],
            podium: [],
            totalCount: 0,
            counts: { all: 0, llm: 0, system: 0, user_bot: 0 },
        };
    }

    const head = rawRows[0];
    const rows = rawRows.filter((r) => r.is_page_row).map(toLeaderboardRow);
    const podium = rawRows
        .filter((r) => r.is_podium)
        .map(toLeaderboardRow)
        .sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));

    return {
        rows,
        podium,
        totalCount: Number(head.total_count ?? rows.length),
        counts: {
            all: Number(head.all_count ?? 0),
            llm: Number(head.llm_count ?? 0),
            system: Number(head.system_count ?? 0),
            user_bot: Number(head.user_bot_count ?? 0),
        },
    };
}
