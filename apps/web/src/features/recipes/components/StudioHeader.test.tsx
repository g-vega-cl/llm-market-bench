import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { StudioHeader } from './StudioHeader';

const baseProps = {
    name: 'Claude Agent Portfolio Mirror',
    onNameChange: vi.fn(),
    onSave: vi.fn(),
    isDirty: false,
    saveState: 'idle' as const,
    saveError: null,
};

describe('StudioHeader', () => {
    it('renders the studio heading, badge, and current strategy name', () => {
        render(<StudioHeader {...baseProps} />);

        expect(screen.getByText('Strategy Builder MVP')).toBeInTheDocument();
        expect(screen.getByText('5-Block Push v2')).toBeInTheDocument();
        expect(screen.getByLabelText('Recipe Name')).toHaveValue('Claude Agent Portfolio Mirror');
    });

    it('forwards name edits and the explicit save', () => {
        const onNameChange = vi.fn();
        const onSave = vi.fn();
        render(<StudioHeader {...baseProps} isDirty onNameChange={onNameChange} onSave={onSave} />);

        fireEvent.change(screen.getByLabelText('Recipe Name'), {
            target: { value: 'Renamed Strategy' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Save Recipe' }));

        expect(onNameChange).toHaveBeenCalledWith('Renamed Strategy');
        expect(onSave).toHaveBeenCalled();
    });

    it('surfaces a save error next to the name field', () => {
        render(<StudioHeader {...baseProps} saveState="error" saveError="PGRST204" />);

        expect(screen.getByRole('alert')).toHaveTextContent('PGRST204');
    });
});
