import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ChainMemorySwitcher } from './ChainMemorySwitcher';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
    useNavigate: () => mockNavigate,
}));

describe('ChainMemorySwitcher', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders featured ticker buttons and search input', () => {
        render(<ChainMemorySwitcher currentMemoryId="m1" />);

        expect(screen.getByText('Switch Chain:')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /\$TSLA/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /\$NVDA/i })).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Search another chain...')).toBeInTheDocument();
    });

    it('searches and navigates when clicking a search result', async () => {
        const mockSearchFn = vi.fn().mockResolvedValue([
            {
                id: 'm2',
                content: 'Tesla delivers 500k vehicles',
                created_at: '2026-05-10T12:00:00Z',
                metadata: { ticker: 'TSLA' },
            },
        ]);

        render(<ChainMemorySwitcher currentMemoryId="m1" searchFn={mockSearchFn} />);

        const input = screen.getByPlaceholderText('Search another chain...');
        fireEvent.change(input, { target: { value: 'TSLA' } });

        await waitFor(() => {
            expect(mockSearchFn).toHaveBeenCalledWith('TSLA');
            expect(screen.getByText('Tesla delivers 500k vehicles')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Tesla delivers 500k vehicles'));

        expect(mockNavigate).toHaveBeenCalledWith({
            to: '/memories/chain/$memoryId',
            params: { memoryId: 'm2' },
        });
    });

    it('triggers search when clicking a featured ticker chip', async () => {
        const mockSearchFn = vi.fn().mockResolvedValue([]);

        render(<ChainMemorySwitcher currentMemoryId="m1" searchFn={mockSearchFn} />);

        const nvdaButton = screen.getByRole('button', { name: /\$NVDA/i });
        fireEvent.click(nvdaButton);

        await waitFor(() => {
            expect(mockSearchFn).toHaveBeenCalledWith('NVDA');
        });
    });
});
