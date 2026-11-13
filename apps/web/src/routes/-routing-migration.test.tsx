import { describe, expect, it } from 'vitest';
import { navItems } from './__root';
import { LAB_CATEGORIES } from './lab';

describe('Routing Migration TDD Verification', () => {
    it('should have B mapped to /, Portfolios to /portfolios, and Lab to /lab in navItems', () => {
        const homeItem = navItems.find((item) => item.to === '/');
        expect(homeItem).toBeDefined();
        expect(homeItem?.ariaLabel).toBe('Home');

        const portfoliosItem = navItems.find((item) => item.to === '/portfolios');
        expect(portfoliosItem).toBeDefined();
        expect(portfoliosItem?.ariaLabel).toBe('Portfolios');

        const labItem = navItems.find((item) => item.to === '/lab');
        expect(labItem).toBeDefined();
        expect(labItem?.ariaLabel).toBe('Lab');
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
