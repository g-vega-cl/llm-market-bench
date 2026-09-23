import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MarketContextViewer } from './MarketContextViewer';

describe('MarketContextViewer', () => {
    it('renders fallback notice when context is null or empty', () => {
        render(<MarketContextViewer context={null} />);
        expect(screen.getByText('Market Context (Model Input)')).toBeInTheDocument();
        expect(
            screen.getByText(
                'Market context was not captured for predictions recorded prior to September 23, 2026.',
            ),
        ).toBeInTheDocument();
    });

    it('renders collapsed preview and allows expanding full text', () => {
        const sampleContext = '=== SAMPLE CONTEXT DATA FOR S&P 500 ===\nOptions Max Pain: $774.00';
        render(<MarketContextViewer context={sampleContext} />);

        // Preview should be visible
        expect(screen.getByText(/SAMPLE CONTEXT DATA/)).toBeInTheDocument();
        expect(screen.getByText('Expand Context')).toBeInTheDocument();

        // Click to expand
        fireEvent.click(screen.getByText('Expand Context'));
        expect(screen.getByText('Collapse Context')).toBeInTheDocument();
        expect(screen.getByText(/Options Max Pain: \$774\.00/)).toBeInTheDocument();
    });

    it('copies text to clipboard when copy button is clicked', async () => {
        const writeTextMock = vi.fn().mockResolvedValue(undefined);
        Object.assign(navigator, {
            clipboard: {
                writeText: writeTextMock,
            },
        });

        const sampleContext = 'Context to be copied';
        render(<MarketContextViewer context={sampleContext} />);

        const copyBtn = screen.getByText('Copy Context');
        await act(async () => {
            fireEvent.click(copyBtn);
        });

        expect(writeTextMock).toHaveBeenCalledWith('Context to be copied');
    });
});
