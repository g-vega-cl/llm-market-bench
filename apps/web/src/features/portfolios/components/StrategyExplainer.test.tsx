import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StrategyExplainer } from './StrategyExplainer';

describe('StrategyExplainer', () => {
    it('renders SMID Quality Compounder thesis and pillars', () => {
        render(<StrategyExplainer ownerId="sys-smid-quality-compounder" />);

        expect(screen.getByText('Small/Mid-Cap Quality Compounder Strategy')).toBeInTheDocument();
        expect(screen.getByText('Zero-Ceiling Invariant')).toBeInTheDocument();
        expect(screen.getByText(/Academic Thesis/i)).toBeInTheDocument();
        expect(screen.getByText(/The Zero-Ceiling Rule/i)).toBeInTheDocument();
        expect(screen.getByText(/Entry Screen/i)).toBeInTheDocument();
        expect(screen.getByText(/Strict Exit Discipline/i)).toBeInTheDocument();
    });

    it('collapses and expands the details panel when clicked', () => {
        render(<StrategyExplainer ownerId="sys-smid-quality-compounder" />);

        // Initially expanded
        expect(screen.getByText(/Asness et al/i)).toBeInTheDocument();

        // Click header to collapse
        const header = screen.getByRole('button');
        fireEvent.click(header);

        expect(screen.queryByText(/Asness et al/i)).not.toBeInTheDocument();
        expect(screen.getByText('Details ▼')).toBeInTheDocument();

        // Click again to re-expand
        fireEvent.click(header);
        expect(screen.getByText(/Asness et al/i)).toBeInTheDocument();
        expect(screen.getByText('Collapse ▲')).toBeInTheDocument();
    });

    it('renders sector long short explainer for sys-sector-ls-consensus', () => {
        render(<StrategyExplainer ownerId="sys-sector-ls-consensus" />);
        expect(screen.getByText('Weekly Sector Long/Short Consensus Strategy')).toBeInTheDocument();
        expect(screen.getByText(/Conflict Netting/i)).toBeInTheDocument();
    });

    it('renders 20d uncorrelated sector momentum explainer', () => {
        render(<StrategyExplainer ownerId="sys-sector-uncorr-20d" />);
        expect(screen.getByText('20-Day Uncorrelated Sector Momentum')).toBeInTheDocument();
        expect(screen.getByText(/Uncorrelated Filter/i)).toBeInTheDocument();
    });

    it('renders 7d uncorrelated sector momentum explainer', () => {
        render(<StrategyExplainer ownerId="sys-sector-uncorr-7d" />);
        expect(screen.getByText('7-Day Uncorrelated Sector Momentum')).toBeInTheDocument();
        expect(screen.getByText(/Low-Beta Pairing/i)).toBeInTheDocument();
    });

    it('renders naive momentum explainer', () => {
        render(<StrategyExplainer ownerId="sys-sector-naive-momentum" />);
        expect(screen.getByText('20-Day Unconstrained Momentum')).toBeInTheDocument();
        expect(screen.getByText(/Control Benchmark/i)).toBeInTheDocument();
    });

    it('renders mean reversion explainer', () => {
        render(<StrategyExplainer ownerId="sys-sector-mean-reversion" />);
        expect(screen.getByText('7-Day Sector Mean Reversion')).toBeInTheDocument();
        expect(screen.getByText(/Oversold Rebound/i)).toBeInTheDocument();
    });

    it('renders daily SPY target exit explainer', () => {
        render(<StrategyExplainer ownerId="sys-daily-spy-deepseek-v4-flash" />);
        expect(screen.getByText('Daily S&P 500 Intraday Trader')).toBeInTheDocument();
        expect(screen.getByText(/Profit Target Exit/i)).toBeInTheDocument();
    });

    it('renders daily SPY 3:50 close exit explainer', () => {
        render(<StrategyExplainer ownerId="sys-daily-spy-close-deepseek-v4-flash" />);
        expect(screen.getByText('Daily S&P 500 Close Trader (3:50 PM Exit)')).toBeInTheDocument();
        expect(screen.getByText(/3:50 PM Close Exit/i)).toBeInTheDocument();
        expect(screen.getByText(/0.02% Liquid Friction/i)).toBeInTheDocument();
    });

    it('returns null for non-system portfolio', () => {
        const { container } = render(<StrategyExplainer ownerId="deepseek-v3" />);
        expect(container.firstChild).toBeNull();
    });
});
