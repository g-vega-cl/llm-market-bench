import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CURATED_TOOLS } from '../types';
import { ToolPicker } from './ToolPicker';

describe('ToolPicker', () => {
    it('excludes web_search from curated recipe tools and marks liveOnly tools with Live only badges', () => {
        expect(CURATED_TOOLS.some((t) => t.name === 'web_search')).toBe(false);
        const liveTools = CURATED_TOOLS.filter((t) => t.liveOnly);
        expect(liveTools.map((t) => t.name)).toEqual(
            expect.arrayContaining([
                'run_stock_screener',
                'get_congress_trades',
                'get_insider_trades',
                'get_whale_holdings',
                'get_government_fiscal_and_spending',
                'get_market_moving_news',
            ]),
        );

        render(<ToolPicker selectedTools={['get_technical_indicators']} onChange={vi.fn()} />);

        expect(screen.queryByText('Web Search')).not.toBeInTheDocument();
        expect(screen.getByText('Stock Screener')).toBeInTheDocument();
        expect(screen.getByText('Congress Trades')).toBeInTheDocument();
        expect(screen.getAllByText('Live only')).toHaveLength(liveTools.length);
    });

    it('excludes legacy disallowed tool names such as web_search from the tool counter badge', () => {
        render(<ToolPicker selectedTools={['get_stock_quote', 'web_search']} onChange={vi.fn()} />);

        expect(screen.getByText(`1 / ${CURATED_TOOLS.length}`)).toBeInTheDocument();
    });
});
