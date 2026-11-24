import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RunPaginator } from './RunPaginator';

describe('RunPaginator', () => {
    it('renders nothing for a single run', () => {
        const { container } = render(
            <RunPaginator index={0} total={1} onOlder={vi.fn()} onNewer={vi.fn()} />,
        );

        expect(container).toBeEmptyDOMElement();
    });

    it('labels the current run and blocks Newer on the newest page without disabling it', () => {
        const onOlder = vi.fn();
        const onNewer = vi.fn();
        render(<RunPaginator index={0} total={3} onOlder={onOlder} onNewer={onNewer} />);

        expect(screen.getByRole('status')).toHaveTextContent('1 of 3');

        const newer = screen.getByRole('button', { name: 'Newer' });
        // aria-disabled, not disabled: disabling the button would drop focus to <body>.
        expect(newer).toHaveAttribute('aria-disabled', 'true');
        expect(newer).not.toBeDisabled();
        fireEvent.click(newer);
        expect(onNewer).not.toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', { name: 'Older' }));
        expect(onOlder).toHaveBeenCalledTimes(1);
    });

    it('blocks Older on the oldest page and keeps Newer live', () => {
        const onOlder = vi.fn();
        const onNewer = vi.fn();
        render(<RunPaginator index={2} total={3} onOlder={onOlder} onNewer={onNewer} />);

        expect(screen.getByRole('status')).toHaveTextContent('3 of 3');

        const older = screen.getByRole('button', { name: 'Older' });
        expect(older).toHaveAttribute('aria-disabled', 'true');
        fireEvent.click(older);
        expect(onOlder).not.toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', { name: 'Newer' }));
        expect(onNewer).toHaveBeenCalledTimes(1);
    });

    it('announces the page and the run it belongs to through one polite region', () => {
        render(
            <RunPaginator
                index={1}
                total={4}
                label="Apr 6 • 8:32 AM ET"
                onOlder={vi.fn()}
                onNewer={vi.fn()}
            />,
        );

        const counter = screen.getByRole('status');
        // role="status" already implies aria-live="polite"; the repo forbids duplicating it.
        expect(counter).not.toHaveAttribute('aria-live');
        expect(counter).toHaveTextContent('2 of 4');
        expect(counter).toHaveTextContent('Apr 6 • 8:32 AM ET');
        // The visible copy stays a bare counter; the run identity is screen-reader only.
        expect(screen.getByText('· Apr 6 • 8:32 AM ET')).toHaveClass('sr-only');
    });

    it('clamps an out-of-range index instead of rendering an impossible page', () => {
        render(<RunPaginator index={5} total={3} onOlder={vi.fn()} onNewer={vi.fn()} />);

        expect(screen.getByRole('status')).toHaveTextContent('3 of 3');
        expect(screen.getByRole('button', { name: 'Older' })).toHaveAttribute(
            'aria-disabled',
            'true',
        );
    });

    it('keeps focus on the boundary control it just made inert', () => {
        render(<RunPaginator index={2} total={3} onOlder={vi.fn()} onNewer={vi.fn()} />);

        const older = screen.getByRole('button', { name: 'Older' });
        older.focus();
        expect(document.activeElement).toBe(older);

        fireEvent.click(older);
        // A `disabled` boundary would blur to <body>; aria-disabled keeps the user's place.
        expect(document.activeElement).toBe(older);
    });

    it('wraps instead of overflowing on a narrow viewport', () => {
        render(<RunPaginator index={0} total={3} onOlder={vi.fn()} onNewer={vi.fn()} />);

        const row = screen.getByRole('status').parentElement;
        expect(row).toHaveClass('flex-wrap');
    });
});
