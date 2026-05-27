import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { MacroStat } from '../lib/macro-tickers';
import { GlobalMacroStats } from './GlobalMacroStats';

const mockMacroStats: MacroStat[] = [
    {
        ticker: 'SPY',
        name: 'S&P 500',
        category: 'Equities',
        price: 500.5,
        todayPctChange: 1.25,
        stdevPct: 0.55,
        regimeFlag: '❗ UNUSUAL',
        hasHistory: true,
    },
    {
        ticker: 'QQQ',
        name: 'Nasdaq 100',
        category: 'Equities',
        price: 400.2,
        todayPctChange: 0.15,
        stdevPct: 0.85,
        regimeFlag: 'Normal',
        hasHistory: true,
    },
    {
        ticker: 'TLT',
        name: '20+yr Treasury',
        category: 'Bonds & Treasury Yields',
        price: 90.5,
        todayPctChange: -2.5,
        stdevPct: 0.45,
        regimeFlag: '⚠️ HIGHLY UNUSUAL',
        hasHistory: true,
    },
    {
        ticker: 'BTCUSD',
        name: 'Bitcoin',
        category: 'Crypto',
        price: 65000,
        todayPctChange: -0.5,
        stdevPct: 1.5,
        regimeFlag: 'Normal',
        hasHistory: true,
    },
];

describe('GlobalMacroStats Component', () => {
    it('renders the header title and category tabs correctly', () => {
        render(<GlobalMacroStats macroStats={mockMacroStats} />);

        expect(screen.getByText('Global Macro Regime')).toBeInTheDocument();
        expect(screen.getByText('Equities')).toBeInTheDocument();
        expect(screen.getByText('Crypto')).toBeInTheDocument();
        expect(screen.getByText('Bonds & Treasury Yields')).toBeInTheDocument();
    });

    it('renders primary indexes as hero benchmark highlights at the top', () => {
        render(<GlobalMacroStats macroStats={mockMacroStats} />);

        // Primary indexes defined are SPY, QQQ. Verify their presence.
        const spyElements = screen.getAllByText('SPY');
        expect(spyElements.length).toBeGreaterThan(0);

        const qqqElements = screen.getAllByText('QQQ');
        expect(qqqElements.length).toBeGreaterThan(0);
    });

    it('filters cards by default active category tab (Equities)', () => {
        render(<GlobalMacroStats macroStats={mockMacroStats} />);

        // In equities category: SPY & QQQ cards (in addition to their hero forms) should be in the document
        expect(screen.getAllByText('SPY')).toHaveLength(2); // Hero + card
        expect(screen.getAllByText('QQQ')).toHaveLength(2); // Hero + card

        // TLT (Bonds) & BTCUSD (Crypto) are NOT in the active "Equities" grid list
        expect(screen.queryByText('TLT')).not.toBeInTheDocument();
        expect(screen.queryByText('BTCUSD')).not.toBeInTheDocument();
    });

    it('allows switching categories via button click and renders bonds explanatory banner', () => {
        render(<GlobalMacroStats macroStats={mockMacroStats} />);

        // Switch to "Bonds & Treasury Yields" category tab
        const bondsTab = screen.getByRole('button', { name: /Bonds & Treasury Yields/i });
        fireEvent.click(bondsTab);

        // Explanatory yields inverse explanation ribbon is now shown!
        expect(screen.getByText(/Bond Prices vs Treasury Yields/i)).toBeInTheDocument();

        // Cards list now contains TLT, but not equities grid list (though SPY/QQQ still in heroes)
        expect(screen.getByText('TLT')).toBeInTheDocument();
        expect(screen.queryByText('BTCUSD')).not.toBeInTheDocument();
    });

    it('renders severe regime badges (REGIME SHIFT, UNUSUAL, Normal) correctly', () => {
        render(<GlobalMacroStats macroStats={mockMacroStats} />);

        // Equities has SPY (❗ UNUSUAL) and QQQ (Normal)
        expect(screen.getAllByText('❗ UNUSUAL').length).toBeGreaterThan(0);

        // Switch to Bonds which has TLT (⚠️ HIGHLY UNUSUAL → REGIME SHIFT)
        fireEvent.click(screen.getByRole('button', { name: /Bonds & Treasury Yields/i }));
        expect(screen.getByText('⚠️ REGIME SHIFT')).toBeInTheDocument();
    });
});
