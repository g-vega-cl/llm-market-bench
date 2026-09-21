import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ExecutionTraceView } from './ExecutionTraceView';

describe('ExecutionTraceView', () => {
    it('returns null when trace is null or empty', () => {
        const { container } = render(<ExecutionTraceView trace={null} />);
        expect(container).toBeEmptyDOMElement();
    });

    it('renders tools and newsletters when provided in trace', () => {
        const mockTrace = {
            active_source_ids: ['news_1', 'news_2'],
            newsletters: [
                {
                    source_id: 'news_1',
                    sender: 'Bloomberg Markets',
                    subject: 'Tech Capex Boom',
                },
            ],
            tools_called: [
                {
                    tool: 'get_stock_quote',
                    ticker: 'NVDA',
                },
                {
                    tool: 'calculate_buy_quantity',
                    ticker: 'NVDA',
                },
            ],
        };

        render(<ExecutionTraceView trace={mockTrace} />);

        expect(screen.getByText('Execution Provenance & Grounding')).toBeInTheDocument();
        expect(screen.getByText('Tools Executed')).toBeInTheDocument();
        expect(screen.getByText('get_stock_quote: NVDA')).toBeInTheDocument();
        expect(screen.getByText('calculate_buy_quantity: NVDA')).toBeInTheDocument();
        expect(screen.getByText(/Bloomberg Markets/)).toBeInTheDocument();
        expect(screen.getByText(/Tech Capex Boom/)).toBeInTheDocument();
    });
});
