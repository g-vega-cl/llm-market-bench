import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RecipeNameField } from './RecipeNameField';

describe('RecipeNameField', () => {
    it('renders the name and keeps saving disabled until the value changes', () => {
        render(
            <RecipeNameField
                value="Chip Momentum"
                onChange={vi.fn()}
                onSave={vi.fn()}
                isDirty={false}
                saveState="idle"
            />,
        );

        expect(screen.getByLabelText('Recipe Name')).toHaveValue('Chip Momentum');
        expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeDisabled();
    });

    it('reports edits and saves explicitly', () => {
        const onChange = vi.fn();
        const onSave = vi.fn();
        render(
            <RecipeNameField
                value="Chip Momentum"
                onChange={onChange}
                onSave={onSave}
                isDirty={true}
                saveState="idle"
            />,
        );

        fireEvent.change(screen.getByLabelText('Recipe Name'), {
            target: { value: 'Semis Rotation' },
        });
        expect(onChange).toHaveBeenCalledWith('Semis Rotation');

        const save = screen.getByRole('button', { name: 'Save Recipe' });
        expect(save).toBeEnabled();
        fireEvent.click(save);
        expect(onSave).toHaveBeenCalledTimes(1);
    });

    it('shows saving, saved, and error states', () => {
        const { rerender } = render(
            <RecipeNameField
                value="Chip Momentum"
                onChange={vi.fn()}
                onSave={vi.fn()}
                isDirty={true}
                saveState="saving"
            />,
        );
        expect(screen.getByRole('button', { name: /Saving/ })).toBeDisabled();

        rerender(
            <RecipeNameField
                value="Chip Momentum"
                onChange={vi.fn()}
                onSave={vi.fn()}
                isDirty={false}
                saveState="saved"
            />,
        );
        expect(screen.getByRole('button', { name: 'Saved' })).toBeDisabled();

        rerender(
            <RecipeNameField
                value="Chip Momentum"
                onChange={vi.fn()}
                onSave={vi.fn()}
                isDirty={true}
                saveState="error"
                errorMessage="Unauthorized: please sign in to save recipes"
            />,
        );
        expect(screen.getByRole('alert')).toHaveTextContent(
            'Unauthorized: please sign in to save recipes',
        );
        expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeEnabled();
    });

    it('disables the input and the button while a recipe is running', () => {
        render(
            <RecipeNameField
                value="Chip Momentum"
                onChange={vi.fn()}
                onSave={vi.fn()}
                isDirty={true}
                saveState="idle"
                disabled={true}
            />,
        );

        expect(screen.getByLabelText('Recipe Name')).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Save Recipe' })).toBeDisabled();
    });
});
