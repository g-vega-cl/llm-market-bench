import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SPYCandlestickChart } from './SPYCandlestickChart';

const mockBars = [
    {
        time: '2026-10-29T14:00:00Z',
        open: 580.0,
        high: 581.5,
        low: 579.5,
        close: 581.0,
        volume: 12000,
    },
    {
        time: '2026-10-29T14:01:00Z',
        open: 581.0,
        high: 582.0,
        low: 580.5,
        close: 580.8,
        volume: 15000,
    },
    {
        time: '2026-10-29T14:02:00Z',
        open: 580.8,
        high: 583.0,
        low: 580.6,
        close: 582.5,
        volume: 22000,
    },
];

const mockTrades = [
    {
        time: '2026-10-29T14:02:00Z',
        action: 'BUY' as const,
        price: 582.5,
        shares: 15,
    },
];

describe('SPYCandlestickChart', () => {
    it('renders empty fallback grid and SVG frame when no bars provided', () => {
        const { container } = render(<SPYCandlestickChart bars={[]} />);
        expect(container.querySelector('svg')).toBeInTheDocument();
        expect(screen.getByText(/awaiting live spy market tape/i)).toBeInTheDocument();
        expect(screen.getByText(/syncing market tape/i)).toBeInTheDocument();
    });

    it('renders SVG chart with bars and trade marker', () => {
        const { container } = render(<SPYCandlestickChart bars={mockBars} trades={mockTrades} />);
        const svg = container.querySelector('svg');
        expect(svg).toBeInTheDocument();
        // Candlestick bodies
        const candleRects = container.querySelectorAll('.candlestick-body');
        expect(candleRects.length).toBe(3);
        // Candlestick wicks
        const candleWicks = container.querySelectorAll('.candlestick-wick');
        expect(candleWicks.length).toBe(3);
        // Trade markers
        const markers = container.querySelectorAll('.trade-marker');
        expect(markers.length).toBe(1);
    });

    it('displays summary metrics bar above chart', () => {
        render(<SPYCandlestickChart bars={mockBars} />);
        expect(screen.getAllByText(/582.50/).length).toBeGreaterThanOrEqual(1);
    });
});
