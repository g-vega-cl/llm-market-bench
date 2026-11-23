import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TurnstileWidget } from './TurnstileWidget';

describe('TurnstileWidget', () => {
    beforeEach(() => {
        delete window.turnstile;
        document.head.innerHTML = '';
    });

    it('renders nothing when no site key is configured', () => {
        const { container } = render(<TurnstileWidget siteKey="" onToken={vi.fn()} />);
        expect(container.firstChild).toBeNull();
    });

    it('renders widget, forwards token callbacks, and resets when resetKey increments', () => {
        const onToken = vi.fn();
        let capturedOptions:
            | {
                  callback?: (token: string) => void;
                  'expired-callback'?: () => void;
              }
            | undefined;

        const renderMock = vi.fn((_el, options) => {
            capturedOptions = options;
            return 'widget-1';
        });
        const resetMock = vi.fn();
        const removeMock = vi.fn();
        window.turnstile = { render: renderMock, reset: resetMock, remove: removeMock };

        const { rerender, unmount } = render(
            <TurnstileWidget siteKey="0x4AAAAAAGOOYupsv82kRp2g" resetKey={0} onToken={onToken} />,
        );

        expect(screen.getByTestId('turnstile-widget')).toBeInTheDocument();
        expect(renderMock).toHaveBeenCalledTimes(1);

        capturedOptions?.callback?.('tok-123');
        expect(onToken).toHaveBeenCalledWith('tok-123');

        capturedOptions?.['expired-callback']?.();
        expect(onToken).toHaveBeenCalledWith(null);

        rerender(
            <TurnstileWidget siteKey="0x4AAAAAAGOOYupsv82kRp2g" resetKey={1} onToken={onToken} />,
        );
        expect(resetMock).toHaveBeenCalledWith('widget-1');
        expect(onToken).toHaveBeenLastCalledWith(null);

        unmount();
        expect(removeMock).toHaveBeenCalledWith('widget-1');
    });
});
