import { describe, expect, it } from 'vitest';
import {
    calculateActualReturns,
    calculateDailyMetrics,
    calculateSpyReturn,
    getAgentDisplayName,
    getCheckpoints,
    getDoNothingReturn,
    getPortfolioReturn,
    getSpyReturn,
    groupPerformanceData,
    type PerformanceRow,
} from './daily-score-math';

describe('daily-score-math', () => {
    describe('getAgentDisplayName', () => {
        it('normalizes recognized agent names', () => {
            expect(getAgentDisplayName('gemini-3.5-flash-lite')).toBe('Gemini 3.5 Flash Lite');
            expect(getAgentDisplayName('gemini_3.1_flash_lite')).toBe('Gemini 3.1 Flash Lite');
            expect(getAgentDisplayName('deepseek-v4-pro')).toBe('DeepSeek V4 Pro');
            expect(getAgentDisplayName('deepseek-v4-flash')).toBe('DeepSeek V4 Flash');
            expect(getAgentDisplayName('claude-haiku-4-5')).toBe('Claude Haiku 4.5');
            expect(getAgentDisplayName('gpt-5.6-luna')).toBe('GPT 5.6 Luna');
            expect(getAgentDisplayName('minimax-m3')).toBe('MiniMax-M3');
        });

        it('returns fallback for unknown or empty IDs', () => {
            expect(getAgentDisplayName(null)).toBe('Unknown Agent');
            expect(getAgentDisplayName(undefined)).toBe('Unknown Agent');
            expect(getAgentDisplayName('custom-agent')).toBe('custom-agent');
        });
    });

    describe('return calculation fallbacks and overrides', () => {
        it('uses explicit metrics returns when present', () => {
            expect(getPortfolioReturn({ portfolio_return_pct: 5.2 }, false, null)).toBe(5.2);
            expect(getSpyReturn({ spy_return_pct: 2.1 }, false, null)).toBe(2.1);
            expect(getDoNothingReturn({ do_nothing_return_pct: 1.8 }, false)).toBe(1.8);
        });

        it('uses active actual returns for portfolio and spy', () => {
            const actuals = {
                agent1: { startEquity: 100, endEquity: 110, actualReturn: 10.0 },
                agent2: { startEquity: 100, endEquity: 120, actualReturn: 20.0 },
            };
            expect(getPortfolioReturn({}, true, actuals)).toBe(15.0);
            expect(getSpyReturn({}, true, 3.4)).toBe(3.4);
        });

        it('falls back to defaults when metrics and actuals are missing', () => {
            expect(getPortfolioReturn({}, true, null)).toBe(1.45);
            expect(getPortfolioReturn({}, false, null)).toBe(0);
            expect(getSpyReturn({}, true, null)).toBe(0.85);
            expect(getSpyReturn({}, false, null)).toBe(0);
            expect(getDoNothingReturn({}, true)).toBe(1.1);
            expect(getDoNothingReturn({}, false)).toBe(0);
        });
    });

    describe('calculateDailyMetrics', () => {
        it('correctly calculates weighted composite excess return and penalty', () => {
            const metrics = {
                portfolio_return_pct: 4.0,
                spy_return_pct: 2.0,
                do_nothing_return_pct: 1.0,
                bond_return_pct: 0.5,
                max_drawdown: 1.0,
            };

            const result = calculateDailyMetrics(metrics, false, null, null);
            // excessVsSpy = 2.0 (0.4 * 2.0 = 0.8)
            // excessVsDoNothing = 3.0 (0.4 * 3.0 = 1.2)
            // excessVsBond = 3.5 (0.2 * 3.5 = 0.7)
            // dailyExcessReturn = 0.8 + 1.2 + 0.7 = 2.7
            // dailyDrawdownPenalty = 1.0 * 0.3 = 0.3
            // dailyScore = 2.7 - 0.3 = 2.4
            expect(result.dailyExcessReturn).toBeCloseTo(2.7, 4);
            expect(result.dailyDrawdownPenalty).toBeCloseTo(0.3, 4);
            expect(result.dailyScore).toBeCloseTo(2.4, 4);
            expect(result.opportunityCost).toBeCloseTo(3.5, 4);
        });
    });

    describe('getCheckpoints', () => {
        it('scales scores across Monday through Friday multipliers', () => {
            const checkpoints = getCheckpoints(10.0, 5.0, '2026-06-01', false);
            expect(checkpoints).toHaveLength(5);
            expect(checkpoints[0].day).toBe('Monday');
            expect(checkpoints[0].score).toBeCloseTo(1.5, 3);
            expect(checkpoints[4].day).toBe('Friday');
            expect(checkpoints[4].score).toBeCloseTo(10.0, 3);
            expect(checkpoints[0].isFuture).toBe(false);
        });
    });

    describe('performance data grouping and actual returns', () => {
        it('groups rows by portfolio_id and computes percentage returns', () => {
            const rows: PerformanceRow[] = [
                {
                    portfolio_id: 'p1',
                    total_equity: 1000,
                    date: '2026-06-01',
                    portfolios: { owner_id: 'agent-alpha' },
                },
                {
                    portfolio_id: 'p1',
                    total_equity: 1100,
                    date: '2026-06-05',
                    portfolios: { owner_id: 'agent-alpha' },
                },
            ];

            const { grouped, ownerIdMap } = groupPerformanceData(rows);
            expect(ownerIdMap.p1).toBe('agent-alpha');
            expect(grouped.p1).toHaveLength(2);

            const returns = calculateActualReturns(grouped, ownerIdMap);
            expect(returns['agent-alpha'].actualReturn).toBeCloseTo(10.0, 2);
            expect(returns['agent-alpha'].startEquity).toBe(1000);
            expect(returns['agent-alpha'].endEquity).toBe(1100);
        });

        it('calculates cumulative compounded SPY return', () => {
            const prices = [{ price: 100 }, { price: 105 }, { price: 110.25 }];
            const spyReturn = calculateSpyReturn(prices);
            expect(spyReturn).toBeCloseTo(10.25, 2);
        });
    });
});
