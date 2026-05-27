import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { MacroStat } from '../lib/macro-tickers';
import { GlobalMacroStats } from './GlobalMacroStats';

const mockMacroStats: MacroStat[] = [
    {
        ticker: 'SPY',
        name: 'S&P 500',
        category: 'Market',
        price: 500.5,
        todayPctChange: 1.25,
        stdevPct: 0.55,
        regimeFlag: '❗ UNUSUAL',
        hasHistory: true,
    },
    {
        ticker: 'TLT',
        name: '20+yr Treasury',
        category: 'Market',
        price: 90.5,
        todayPctChange: -2.5,
        stdevPct: 0.45,
        regimeFlag: '⚠️ HIGHLY UNUSUAL',
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
        ticker: 'IEF',
        name: '7-10yr Treasury',
        category: 'Bonds & Treasury Yields',
        price: 95.0,
        todayPctChange: -0.1,
        stdevPct: 0.3,
        regimeFlag: 'Normal',
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
        expect(screen.getByText('Market')).toBeInTheDocument();
        expect(screen.getByText('Equities')).toBeInTheDocument();
        expect(screen.getByText('Crypto')).toBeInTheDocument();
        expect(screen.getByText('Bonds & Treasury Yields')).toBeInTheDocument();
    });

    it('filters cards by default active category tab (Market)', () => {
        render(<GlobalMacroStats macroStats={mockMacroStats} />);

        // In Market category: SPY & TLT cards should be in the document
        expect(screen.getByText('SPY')).toBeInTheDocument();
        expect(screen.getByText('TLT')).toBeInTheDocument();

        // QQQ (Equities) & BTCUSD (Crypto) are NOT in the active "Market" grid list
        expect(screen.queryByText('QQQ')).not.toBeInTheDocument();
        expect(screen.queryByText('BTCUSD')).not.toBeInTheDocument();
    });

    it('allows switching categories via button click and renders bonds explanatory banner', () => {
        render(<GlobalMacroStats macroStats={mockMacroStats} />);

        // Switch to "Bonds & Treasury Yields" category tab
        const bondsTab = screen.getByRole('button', { name: /Bonds & Treasury Yields/i });
        fireEvent.click(bondsTab);

        // Explanatory yields inverse explanation ribbon is now shown!
        expect(screen.getByText(/Bond Prices vs Treasury Yields/i)).toBeInTheDocument();

        // Cards list now contains IEF, but not equities/market grid list
        expect(screen.getByText('IEF')).toBeInTheDocument();
        expect(screen.queryByText('SPY')).not.toBeInTheDocument();
        expect(screen.queryByText('TLT')).not.toBeInTheDocument();
        expect(screen.queryByText('BTCUSD')).not.toBeInTheDocument();
    });

    it('renders severe regime badges (REGIME SHIFT, UNUSUAL, Normal) correctly', () => {
        render(<GlobalMacroStats macroStats={mockMacroStats} />);

        // Default 'Market' has SPY (❗ UNUSUAL) and TLT (⚠️ HIGHLY UNUSUAL -> REGIME SHIFT)
        expect(screen.getByText('❗ UNUSUAL')).toBeInTheDocument();
        expect(screen.getByText('⚠️ REGIME SHIFT')).toBeInTheDocument();
    });
});
