import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { TypeCodeGrid } from './TypeCodeGrid';

const CODES = [
    'LVFP',
    'LVFR',
    'LVMP',
    'LVMR',
    'LNFP',
    'LNFR',
    'LNMP',
    'LNMR',
    'QVFP',
    'QVFR',
    'QVMP',
    'QVMR',
    'QNFP',
    'QNFR',
    'QNMP',
    'QNMR',
];

const CELLS = CODES.map((code) => ({ code, label: `Type ${code}` }));
const ROWS = ['LV', 'LN', 'QV', 'QN'];
const COLUMNS = ['FP', 'FR', 'MP', 'MR'];

describe('TypeCodeGrid', () => {
    it('renders all 16 codes in a 4x4 grid with headers and no nested scroll container', () => {
        render(
            <TypeCodeGrid
                testId="type-grid"
                cells={CELLS}
                activeCode="LVFP"
                onSelect={vi.fn()}
                rowHeaders={ROWS}
                columnHeaders={COLUMNS}
            />,
        );

        const grid = screen.getByTestId('type-grid');
        const buttons = within(grid).getAllByRole('button');
        expect(buttons).toHaveLength(16);
        for (const code of CODES) {
            expect(
                within(grid).getByRole('button', { name: new RegExp(code) }),
            ).toBeInTheDocument();
        }
        for (const header of [...ROWS, ...COLUMNS]) {
            expect(within(grid).getByText(header)).toBeInTheDocument();
        }
        expect(grid.querySelectorAll('.overflow-y-auto')).toHaveLength(0);
        expect(grid.querySelector('.grid')).not.toBeNull();
    });

    it('marks only the active cell pressed and reports selections by code', () => {
        const onSelect = vi.fn();
        render(
            <TypeCodeGrid
                testId="type-grid"
                cells={CELLS}
                activeCode="LNFR"
                onSelect={onSelect}
                rowHeaders={ROWS}
                columnHeaders={COLUMNS}
            />,
        );

        const pressed = within(screen.getByTestId('type-grid'))
            .getAllByRole('button')
            .filter((button) => button.getAttribute('aria-pressed') === 'true');
        expect(pressed).toHaveLength(1);
        expect(pressed[0]).toHaveAccessibleName(/LNFR/);

        fireEvent.click(screen.getByRole('button', { name: /QNMR/ }));
        expect(onSelect).toHaveBeenCalledWith('QNMR');
    });

    it('renders the active cell description in flow rather than as a hover affordance', () => {
        render(
            <TypeCodeGrid
                testId="type-grid"
                cells={CELLS}
                activeCode="LVFP"
                onSelect={vi.fn()}
                rowHeaders={ROWS}
                columnHeaders={COLUMNS}
                description="The Patient Compounder · Quality Value Screener"
            />,
        );

        const description = screen.getByTestId('type-grid-description');
        expect(description).toHaveTextContent('The Patient Compounder');
        expect(description).not.toHaveAttribute('title');
        expect(description.className).toContain('break-words');
    });
});
