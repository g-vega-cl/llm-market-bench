import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PromoteMemoryModal } from './PromoteMemoryModal';

describe('PromoteMemoryModal Component', () => {
    const defaultData = {
        ticker: 'NVO',
        thesis: 'NVO margin pressure due to manufacturing capex and LLY competition.',
        tags: ['GLP-1', 'pharma'],
        importance_score: 8,
    };

    it('renders with prefilled distilled values', () => {
        render(
            <PromoteMemoryModal
                isOpen={true}
                onClose={vi.fn()}
                userQuery="Should I invest in NVO?"
                assistantResponse="NVO analysis..."
                initialData={defaultData}
                onSave={vi.fn()}
                onRedistill={vi.fn()}
                onSavedSuccess={vi.fn()}
            />,
        );

        expect(screen.getByText(/Promote Insight to Private Memory/i)).toBeInTheDocument();
        expect(screen.getByDisplayValue('NVO')).toBeInTheDocument();
        expect(screen.getByDisplayValue(defaultData.thesis)).toBeInTheDocument();
        expect(screen.getByDisplayValue('8')).toBeInTheDocument();
        expect(screen.getByText('GLP-1')).toBeInTheDocument();
        expect(screen.getByText('pharma')).toBeInTheDocument();
    });

    it('allows editing fields and submitting saved thesis', async () => {
        const mockOnSave = vi.fn().mockResolvedValue({
            id: 'saved-mem-1',
            user_id: 'user-1',
            ticker: 'NVO',
            thesis: 'Edited thesis with updated timeline.',
            tags: ['GLP-1', 'pharma'],
            importance_score: 9,
            created_at: '2026-09-04T12:00:00Z',
        });
        const mockOnSuccess = vi.fn();
        const mockOnClose = vi.fn();

        render(
            <PromoteMemoryModal
                isOpen={true}
                onClose={mockOnClose}
                userQuery="Should I invest in NVO?"
                assistantResponse="NVO analysis..."
                initialData={defaultData}
                onSave={mockOnSave}
                onRedistill={vi.fn()}
                onSavedSuccess={mockOnSuccess}
            />,
        );

        const thesisInput = screen.getByDisplayValue(defaultData.thesis);
        fireEvent.change(thesisInput, {
            target: { value: 'Edited thesis with updated timeline.' },
        });

        const scoreInput = screen.getByDisplayValue('8');
        fireEvent.change(scoreInput, { target: { value: '9' } });

        const saveButton = screen.getByRole('button', { name: /Save to My Theses/i });
        fireEvent.click(saveButton);

        await waitFor(() => {
            expect(mockOnSave).toHaveBeenCalledWith({
                ticker: 'NVO',
                thesis: 'Edited thesis with updated timeline.',
                tags: ['GLP-1', 'pharma'],
                importance_score: 9,
                sourceQuery: 'Should I invest in NVO?',
            });
            expect(mockOnSuccess).toHaveBeenCalled();
            expect(mockOnClose).toHaveBeenCalled();
        });
    });

    it('triggers re-distillation when custom instruction is submitted', async () => {
        const mockOnRedistill = vi.fn().mockResolvedValue({
            ticker: 'NVO',
            thesis: 'New thesis focusing strictly on manufacturing bottlenecks.',
            tags: ['supply-chain'],
            importance_score: 9,
        });

        render(
            <PromoteMemoryModal
                isOpen={true}
                onClose={vi.fn()}
                userQuery="Should I invest in NVO?"
                assistantResponse="NVO analysis..."
                initialData={defaultData}
                onSave={vi.fn()}
                onRedistill={mockOnRedistill}
                onSavedSuccess={vi.fn()}
            />,
        );

        const customInstructionInput = screen.getByPlaceholderText(/Focus on supply bottleneck/i);
        fireEvent.change(customInstructionInput, {
            target: { value: 'Focus strictly on manufacturing supply' },
        });

        const redistillButton = screen.getByRole('button', { name: /Re-distill/i });
        fireEvent.click(redistillButton);

        await waitFor(() => {
            expect(mockOnRedistill).toHaveBeenCalledWith('Focus strictly on manufacturing supply');
            expect(
                screen.getByDisplayValue(
                    'New thesis focusing strictly on manufacturing bottlenecks.',
                ),
            ).toBeInTheDocument();
        });
    });
});
