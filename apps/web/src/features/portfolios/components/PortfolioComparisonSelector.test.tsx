import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PortfolioComparisonSelector } from './PortfolioComparisonSelector';

describe('PortfolioComparisonSelector', () => {
    const mockAvailable = [
        { portfolioId: 'p-1', ownerId: 'agent-alpha' },
        { portfolioId: 'p-2', ownerId: 'agent-beta' },
        { portfolioId: 'p-3', ownerId: 'agent-gamma' },
        { portfolioId: 'p-4', ownerId: 'agent-delta' },
        { portfolioId: 'p-5', ownerId: 'agent-epsilon' },
        { portfolioId: 'p-6', ownerId: 'agent-zeta' },
    ];

    const mockColors = {
        'p-1': '#0ea5e9',
        'p-2': '#10b981',
        'p-3': '#8b5cf6',
        'p-4': '#ec4899',
        'p-5': '#06b6d4',
        'p-6': '#f59e0b',
    };

    it('renders selected portfolios as chips with their remove buttons', () => {
        const onRemove = vi.fn();
        const onAdd = vi.fn();

        render(
            <PortfolioComparisonSelector
                availablePortfolios={mockAvailable}
                selectedIds={['p-1', 'p-2', 'p-3']}
                portfolioColors={mockColors}
                onAdd={onAdd}
                onRemove={onRemove}
            />,
        );

        expect(screen.getByText('agent alpha')).toBeInTheDocument();
        expect(screen.getByText('agent beta')).toBeInTheDocument();
        expect(screen.getByText('agent gamma')).toBeInTheDocument();
        expect(screen.getByText('3 / 5')).toBeInTheDocument();

        // Click remove on agent-alpha
        const removeButton = screen.getByRole('button', {
            name: /remove agent alpha from comparison/i,
        });
        fireEvent.click(removeButton);
        expect(onRemove).toHaveBeenCalledWith('p-1');
    });

    it('allows user to select and add an unselected portfolio when count is less than 5', () => {
        const onAdd = vi.fn();
        const onRemove = vi.fn();

        render(
            <PortfolioComparisonSelector
                availablePortfolios={mockAvailable}
                selectedIds={['p-1', 'p-2']}
                portfolioColors={mockColors}
                onAdd={onAdd}
                onRemove={onRemove}
            />,
        );

        const select = screen.getByRole('combobox', {
            name: /add agent to comparison/i,
        });
        expect(select).not.toBeDisabled();

        fireEvent.change(select, { target: { value: 'p-3' } });
        expect(onAdd).toHaveBeenCalledWith('p-3');
    });

    it('disables the add selector when max limit of 5 is reached', () => {
        const onAdd = vi.fn();
        const onRemove = vi.fn();

        render(
            <PortfolioComparisonSelector
                availablePortfolios={mockAvailable}
                selectedIds={['p-1', 'p-2', 'p-3', 'p-4', 'p-5']}
                portfolioColors={mockColors}
                onAdd={onAdd}
                onRemove={onRemove}
            />,
        );

        expect(screen.getByText('5 / 5')).toBeInTheDocument();
        const select = screen.getByRole('combobox', {
            name: /add agent to comparison/i,
        });
        expect(select).toBeDisabled();
        expect(screen.getByText('+ Add Agent (Max 5)')).toBeInTheDocument();
    });

    it('supports showing fewer than 5 portfolios, including 0 portfolios', () => {
        render(
            <PortfolioComparisonSelector
                availablePortfolios={mockAvailable}
                selectedIds={[]}
                portfolioColors={mockColors}
                onAdd={vi.fn()}
                onRemove={vi.fn()}
            />,
        );

        expect(screen.getByText('0 / 5')).toBeInTheDocument();
        expect(screen.getByText(/no agents selected/i)).toBeInTheDocument();
    });

    it('calls onReset when Reset to Top 5 button is clicked', () => {
        const onReset = vi.fn();

        render(
            <PortfolioComparisonSelector
                availablePortfolios={mockAvailable}
                selectedIds={['p-1']}
                portfolioColors={mockColors}
                onAdd={vi.fn()}
                onRemove={vi.fn()}
                onReset={onReset}
            />,
        );

        const resetButton = screen.getByRole('button', { name: /reset to top 5/i });
        fireEvent.click(resetButton);
        expect(onReset).toHaveBeenCalledTimes(1);
    });
});
