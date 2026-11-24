import { createServerFn } from '@tanstack/react-start';
import { BENCHMARK_OPTIONS } from '../components/BenchmarkSelector';
import { fetchBenchmarkHistory } from './fetch-portfolios';

const ALLOWED_BENCHMARK_TICKERS = new Set(BENCHMARK_OPTIONS.map((opt) => opt.ticker));
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export const getBenchmarkHistoryFn = createServerFn({ method: 'GET' })
    .validator((d: { tickers: string[]; startDate: string; endDate: string }) => d)
    .handler(async ({ data }) => {
        const tickers = (data.tickers ?? []).filter((t) => ALLOWED_BENCHMARK_TICKERS.has(t));
        if (
            tickers.length === 0 ||
            !ISO_DATE_RE.test(data.startDate) ||
            !ISO_DATE_RE.test(data.endDate)
        ) {
            return {};
        }
        return fetchBenchmarkHistory(tickers, data.startDate, data.endDate);
    });
