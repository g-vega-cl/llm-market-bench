import { fireEvent, render, screen } from '@testing-library/react';
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

    it('matches trade with sub-minute seconds/milliseconds to the enclosing 1-minute bar', () => {
        const unalignedTrades = [
            {
                time: '2026-10-29T14:01:23.456Z',
                action: 'SELL' as const,
                price: 581.2,
                shares: 20,
            },
        ];
        const { container } = render(
            <SPYCandlestickChart bars={mockBars} trades={unalignedTrades} />,
        );
        const markers = container.querySelectorAll('.trade-marker');
        expect(markers.length).toBe(1);
    });

    it('offsets multiple trades occurring within the same 1-minute candlestick', () => {
        const multiTrades = [
            {
                time: '2026-10-29T14:02:10Z',
                action: 'BUY' as const,
                price: 582.1,
                shares: 10,
            },
            {
                time: '2026-10-29T14:02:40Z',
                action: 'BUY' as const,
                price: 582.4,
                shares: 25,
            },
        ];
        const { container } = render(<SPYCandlestickChart bars={mockBars} trades={multiTrades} />);
        const markers = container.querySelectorAll('.trade-marker');
        expect(markers.length).toBe(2);
        const transform1 = markers[0].getAttribute('transform');
        const transform2 = markers[1].getAttribute('transform');
        expect(transform1).not.toBe(transform2);
    });

    it('opens and dismisses trade description slot on marker click with full telemetry and active highlight', () => {
        const testTrades = [
            {
                id: 't-1',
                time: '2026-10-29T14:02:15Z',
                action: 'BUY' as const,
                price: 582.5,
                shares: 100,
            },
        ];
        const { container } = render(<SPYCandlestickChart bars={mockBars} trades={testTrades} />);

        // Before click, no description slot
        expect(screen.queryByTestId('selected-trade-slot')).not.toBeInTheDocument();

        // Marker must have zero <title> tags to forbid native browser tooltips
        expect(container.querySelectorAll('.trade-marker title')).toHaveLength(0);

        // Marker must have accessible button role and hit target
        const marker = container.querySelector('.trade-marker');
        expect(marker).not.toBeNull();
        expect(marker?.getAttribute('role')).toBe('button');
        expect(marker?.getAttribute('tabindex')).toBe('0');
        expect(marker?.getAttribute('aria-label')).toMatch(/BUY trade at \$582\.50/);

        // Keyboard navigation (Enter key) selects the marker
        if (marker) {
            fireEvent.keyDown(marker, { key: 'Enter' });
        }

        // Now description slot is rendered with full telemetry
        const slot = screen.getByTestId('selected-trade-slot');
        expect(slot).toBeInTheDocument();
        expect(slot).toHaveTextContent(/BUY/);
        expect(slot).toHaveTextContent(/100\s*sh/i);
        expect(slot).toHaveTextContent(/\$582\.50/);
        expect(slot).toHaveTextContent(/\$58,250\.00/); // 100 * 582.50
        expect(slot).toHaveTextContent(/ET/);

        // Selected marker path has accent highlight stroke
        const selectedMarker = container.querySelector('.trade-marker.is-selected');
        expect(selectedMarker).not.toBeNull();
        const markerPath = selectedMarker?.querySelector('path');
        expect(markerPath?.getAttribute('stroke')).toBe('#f59e0b');

        // Re-clicking selected marker toggles/deselects it
        const newSelectedMarker = container.querySelector('.trade-marker.is-selected');
        expect(newSelectedMarker).not.toBeNull();
        if (newSelectedMarker) {
            fireEvent.click(newSelectedMarker);
        }
        expect(screen.queryByTestId('selected-trade-slot')).not.toBeInTheDocument();

        // Clicking marker again opens slot, clicking SVG background dismisses it
        const reOpenedMarker = container.querySelector('.trade-marker');
        expect(reOpenedMarker).not.toBeNull();
        if (reOpenedMarker) {
            fireEvent.click(reOpenedMarker);
        }
        expect(screen.getByTestId('selected-trade-slot')).toBeInTheDocument();
        const svg = container.querySelector('svg');
        expect(svg).not.toBeNull();
        if (svg) {
            fireEvent.click(svg);
        }
        expect(screen.queryByTestId('selected-trade-slot')).not.toBeInTheDocument();
    });
});
