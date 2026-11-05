import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useWindowFocusRefresh } from './useWindowFocusRefresh';

describe('useWindowFocusRefresh', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        Object.defineProperty(document, 'hidden', {
            configurable: true,
            value: false,
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    it('triggers onRefresh when window receives a focus event', () => {
        const onRefresh = vi.fn();
        renderHook(() =>
            useWindowFocusRefresh({
                onRefresh,
                throttleMs: 5000,
            }),
        );

        // Fast-forward past initial cooldown
        vi.advanceTimersByTime(5001);

        act(() => {
            window.dispatchEvent(new Event('focus'));
        });

        expect(onRefresh).toHaveBeenCalledTimes(1);
    });

    it('triggers onRefresh when document visibilitychange occurs and document is visible', () => {
        const onRefresh = vi.fn();
        Object.defineProperty(document, 'hidden', {
            configurable: true,
            value: false,
        });

        renderHook(() =>
            useWindowFocusRefresh({
                onRefresh,
                throttleMs: 5000,
            }),
        );

        vi.advanceTimersByTime(5001);

        act(() => {
            document.dispatchEvent(new Event('visibilitychange'));
        });

        expect(onRefresh).toHaveBeenCalledTimes(1);
    });

    it('ignores visibilitychange if document is hidden', () => {
        const onRefresh = vi.fn();
        Object.defineProperty(document, 'hidden', {
            configurable: true,
            value: true,
        });

        renderHook(() =>
            useWindowFocusRefresh({
                onRefresh,
                throttleMs: 5000,
            }),
        );

        vi.advanceTimersByTime(5001);

        act(() => {
            document.dispatchEvent(new Event('visibilitychange'));
        });

        expect(onRefresh).not.toHaveBeenCalled();
    });

    it('throttles rapid focus events within throttleMs window', () => {
        const onRefresh = vi.fn();
        renderHook(() =>
            useWindowFocusRefresh({
                onRefresh,
                throttleMs: 5000,
            }),
        );

        vi.advanceTimersByTime(5001);

        // First focus event
        act(() => {
            window.dispatchEvent(new Event('focus'));
        });
        expect(onRefresh).toHaveBeenCalledTimes(1);

        // Immediate subsequent focus event (within 1 second)
        vi.advanceTimersByTime(1000);
        act(() => {
            window.dispatchEvent(new Event('focus'));
        });
        expect(onRefresh).toHaveBeenCalledTimes(1);

        // Advance past throttleMs (4000ms more = 5000ms total since last refresh)
        vi.advanceTimersByTime(4001);
        act(() => {
            window.dispatchEvent(new Event('focus'));
        });
        expect(onRefresh).toHaveBeenCalledTimes(2);
    });

    it('reloads PostHog feature flags and captures telemetry event when posthog is provided', () => {
        const onRefresh = vi.fn();
        const mockReloadFeatureFlags = vi.fn();
        const mockCapture = vi.fn();

        const posthog = {
            reloadFeatureFlags: mockReloadFeatureFlags,
            capture: mockCapture,
        };

        renderHook(() =>
            useWindowFocusRefresh({
                onRefresh,
                throttleMs: 5000,
                posthog,
            }),
        );

        vi.advanceTimersByTime(5001);

        act(() => {
            window.dispatchEvent(new Event('focus'));
        });

        expect(onRefresh).toHaveBeenCalledTimes(1);
        expect(mockReloadFeatureFlags).toHaveBeenCalledTimes(1);
        expect(mockCapture).toHaveBeenCalledWith('window_focus_refreshed', { path: '/' });
    });

    it('cleans up event listeners on unmount', () => {
        const onRefresh = vi.fn();
        const { unmount } = renderHook(() =>
            useWindowFocusRefresh({
                onRefresh,
                throttleMs: 5000,
            }),
        );

        unmount();
        vi.advanceTimersByTime(5001);

        act(() => {
            window.dispatchEvent(new Event('focus'));
            document.dispatchEvent(new Event('visibilitychange'));
        });

        expect(onRefresh).not.toHaveBeenCalled();
    });

    it('does not register listeners when enabled is false', () => {
        const onRefresh = vi.fn();
        renderHook(() =>
            useWindowFocusRefresh({
                onRefresh,
                enabled: false,
            }),
        );

        vi.advanceTimersByTime(5001);

        act(() => {
            window.dispatchEvent(new Event('focus'));
        });

        expect(onRefresh).not.toHaveBeenCalled();
    });
});
