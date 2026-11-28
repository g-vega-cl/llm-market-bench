import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LiveWeekBanner, lapsedLiveWeek } from './LiveWeekBanner';

vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

const NOW = Date.parse('2026-11-27T18:00:00Z');
const LAST_WEEK = '2026-11-20T14:30:00+00:00';
const NEXT_WEEK = '2026-12-04T14:30:00+00:00';

describe('lapsedLiveWeek', () => {
    it('reports the date only for a lapsed, paused bot', () => {
        expect(lapsedLiveWeek(false, LAST_WEEK, NOW)).toBe('2026-11-20');
        expect(lapsedLiveWeek(true, LAST_WEEK, NOW)).toBeNull();
        expect(lapsedLiveWeek(false, NEXT_WEEK, NOW)).toBeNull();
        expect(lapsedLiveWeek(false, null, NOW)).toBeNull();
        expect(lapsedLiveWeek(false, undefined, NOW)).toBeNull();
        expect(lapsedLiveWeek(false, 'not-a-date', NOW)).toBeNull();
    });
});

describe('LiveWeekBanner', () => {
    it('offers the owner a one-token renewal', () => {
        const onRenew = vi.fn();
        render(
            <LiveWeekBanner isOwner isLive={false} liveExpiresAt={LAST_WEEK} onRenew={onRenew} />,
        );

        expect(screen.getByTestId('live-week-banner').textContent).toContain('2026-11-20');
        fireEvent.click(screen.getByText('Renew for 1 token'));
        expect(onRenew).toHaveBeenCalledOnce();
    });

    it('disables the button while a renewal is in flight', () => {
        render(<LiveWeekBanner isOwner isLive={false} liveExpiresAt={LAST_WEEK} busy />);
        expect(screen.getByText('Renewing…')).toBeDisabled();
    });

    it('asks a visitor to sign in instead of offering a spend', () => {
        render(<LiveWeekBanner isOwner={false} isLive={false} liveExpiresAt={LAST_WEEK} />);
        expect(
            screen.getByText('Sign in to claim this bot').closest('a')?.getAttribute('href'),
        ).toBe('/signup');
        expect(screen.queryByText('Renew for 1 token')).toBeNull();
    });

    it('renders nothing while the week is still running', () => {
        const { container } = render(
            <LiveWeekBanner isOwner isLive={false} liveExpiresAt={NEXT_WEEK} />,
        );
        expect(container.firstChild).toBeNull();
    });
});
