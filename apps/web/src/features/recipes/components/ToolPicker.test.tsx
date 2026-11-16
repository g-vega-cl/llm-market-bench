import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CURATED_TOOLS } from '../types';
import { ToolPicker } from './ToolPicker';

describe('ToolPicker', () => {
    it('excludes web_search from curated recipe tools and marks run_stock_screener as Live only', () => {
        expect(CURATED_TOOLS.some((t) => t.name === 'web_search')).toBe(false);

        render(<ToolPicker selectedTools={['get_technical_indicators']} onChange={vi.fn()} />);

        expect(screen.queryByText('Web Search')).not.toBeInTheDocument();
        expect(screen.getByText('Stock Screener')).toBeInTheDocument();
        expect(screen.getByText('Live only')).toBeInTheDocument();
    });

    it('excludes legacy disallowed tool names such as web_search from the tool counter badge', () => {
        render(<ToolPicker selectedTools={['get_stock_quote', 'web_search']} onChange={vi.fn()} />);

        expect(screen.getByText(`1 / ${CURATED_TOOLS.length}`)).toBeInTheDocument();
    });
});
