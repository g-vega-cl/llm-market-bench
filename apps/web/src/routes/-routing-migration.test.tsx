import { describe, expect, it } from 'vitest';
import { navItems } from './__root';
import { LAB_CATEGORIES } from './lab';

describe('Routing Migration TDD Verification', () => {
    it('should have Home mapped to /, Portfolios to /portfolios, and Lab to /lab in navItems', () => {
        const homeItem = navItems.find((item) => item.label === 'Home');
        expect(homeItem).toBeDefined();
        expect(homeItem?.to).toBe('/');

        const portfoliosItem = navItems.find((item) => item.label === 'Portfolios');
        expect(portfoliosItem).toBeDefined();
        expect(portfoliosItem?.to).toBe('/portfolios');

        const labItem = navItems.find((item) => item.label === 'Lab');
        expect(labItem).toBeDefined();
        expect(labItem?.to).toBe('/lab');
    });

    it('should map Backtests item to /autoresearch-backtest in the Lab directory', () => {
        const allLabItems = LAB_CATEGORIES.flatMap((c) => c.items);
        const backtestItem = allLabItems.find(
            (item) => item.label === 'Backtests' || item.label === 'Backtest',
        );
        expect(backtestItem).toBeDefined();
        expect(backtestItem?.to).toBe('/autoresearch-backtest');
    });
});
