import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import { TemplatePickerBar } from './TemplatePickerBar';

describe('TemplatePickerBar', () => {
    it('renders one button per template and the selected description', () => {
        render(
            <TemplatePickerBar templates={STARTER_RECIPES} activeIndex={1} onSelect={vi.fn()} />,
        );

        expect(screen.getAllByRole('button')).toHaveLength(STARTER_RECIPES.length);
        expect(screen.getByTestId('template-description')).toHaveTextContent(
            STARTER_RECIPES[1].description ?? '',
        );
        expect(screen.getByRole('button', { name: STARTER_RECIPES[1].name })).toBeInTheDocument();
    });

    it('reports the chosen template index', () => {
        const onSelect = vi.fn();
        render(
            <TemplatePickerBar templates={STARTER_RECIPES} activeIndex={0} onSelect={onSelect} />,
        );

        fireEvent.click(screen.getByRole('button', { name: STARTER_RECIPES[3].name }));

        expect(onSelect).toHaveBeenCalledWith(3);
    });

    it('hides the description when the studio is editing a saved recipe', () => {
        render(
            <TemplatePickerBar templates={STARTER_RECIPES} activeIndex={-1} onSelect={vi.fn()} />,
        );

        expect(screen.queryByTestId('template-description')).not.toBeInTheDocument();
    });

    it('disables every template button while the studio is busy', () => {
        render(
            <TemplatePickerBar
                templates={STARTER_RECIPES}
                activeIndex={0}
                onSelect={vi.fn()}
                disabled
            />,
        );

        for (const button of screen.getAllByRole('button')) {
            expect(button).toBeDisabled();
        }
    });
});
