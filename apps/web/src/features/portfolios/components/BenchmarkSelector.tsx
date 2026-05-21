export interface BenchmarkOption {
    label: string;
    ticker: string;
    description: string;
}

export const BENCHMARK_OPTIONS: BenchmarkOption[] = [
    { label: 'S&P 500', ticker: 'SPY', description: 'US Large Cap' },
    { label: 'Nasdaq 100', ticker: 'QQQ', description: 'US Tech' },
    { label: 'Total World', ticker: 'URTH', description: 'Global Equity' },
    { label: 'Gold', ticker: 'GLD', description: 'Commodities' },
    { label: 'Copper', ticker: 'CPER', description: 'Industrial Metals' },
    { label: 'Natural Gas', ticker: 'UNG', description: 'Energy' },
    { label: 'Long Treasuries', ticker: 'TLT', description: 'Bonds' },
    { label: 'TIPS', ticker: 'TIP', description: 'Inflation Protected' },
    { label: 'Bitcoin', ticker: 'BTCUSD', description: 'Crypto' },
    { label: 'Euro Stoxx', ticker: 'VGK', description: 'Europe' },
    { label: 'Japan Nikkei', ticker: 'EWJ', description: 'Japan' },
    { label: 'UK FTSE', ticker: 'EWU', description: 'United Kingdom' },
    { label: 'Canada TSX', ticker: 'EWC', description: 'Canada' },
    { label: 'Emerging Markets', ticker: 'EEM', description: 'EM Equity' },
    { label: 'Russell 2000', ticker: 'IWM', description: 'US Small Cap' },
    { label: 'Dow Jones', ticker: 'DIA', description: 'US Blue Chip' },
];

interface BenchmarkSelectorProps {
    selected: string;
    onChange: (ticker: string) => void;
}

export function BenchmarkSelector({ selected, onChange }: BenchmarkSelectorProps) {
    return (
        <div className="flex flex-wrap items-center gap-3">
            <label
                htmlFor="benchmark-select"
                className="text-sm font-medium text-zinc-600 uppercase tracking-wider whitespace-nowrap"
            >
                Benchmark
            </label>
            <select
                id="benchmark-select"
                value={selected}
                onChange={(e) => onChange(e.target.value)}
                className="bg-white border border-zinc-300 rounded-lg px-3 py-2 text-sm font-medium text-zinc-800 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent cursor-pointer max-w-full"
            >
                <option value="">None</option>
                {BENCHMARK_OPTIONS.map((opt) => (
                    <option key={opt.ticker} value={opt.ticker}>
                        {opt.label} ({opt.ticker})
                    </option>
                ))}
            </select>
        </div>
    );
}
