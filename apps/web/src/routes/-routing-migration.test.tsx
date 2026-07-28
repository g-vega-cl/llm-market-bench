import { describe, expect, it } from 'vitest';
import { navItems } from './__root';

describe('Routing Migration TDD Verification', () => {
    it('should have Home mapped to / and Today mapped to /today', () => {
        const homeItem = navItems.find((item) => item.label === 'Home');
        expect(homeItem).toBeDefined();
        expect(homeItem?.to).toBe('/');

        const todayItem = navItems.find((item) => item.label === 'Today');
        expect(todayItem).toBeDefined();
        expect(todayItem?.to).toBe('/today');
    });

    it('should map Backtests navigation item to /autoresearch-backtest', () => {
        const backtestItem = navItems.find(
            (item) => item.label === 'Backtests' || item.label === 'Backtest',
        );
        expect(backtestItem).toBeDefined();
        expect(backtestItem?.to).toBe('/autoresearch-backtest');
    });
});
