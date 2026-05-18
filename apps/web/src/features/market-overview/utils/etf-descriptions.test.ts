import { describe, expect, it } from 'vitest';
import { etfDescriptions } from './etf-descriptions';

describe('etfDescriptions', () => {
    it('should contain full names for known tickers', () => {
        expect(etfDescriptions.SPY).toBe('SPDR S&P 500 ETF Trust');
        expect(etfDescriptions.QQQ).toBe('Invesco QQQ Trust (NASDAQ 100)');
        expect(etfDescriptions.GLD).toBe('SPDR Gold Shares');
    });

    it('should return undefined for unknown tickers', () => {
        expect(etfDescriptions.UNKNOWN).toBeUndefined();
    });
});
