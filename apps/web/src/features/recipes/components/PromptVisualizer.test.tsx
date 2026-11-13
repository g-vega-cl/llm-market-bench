import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import { PromptVisualizer } from './PromptVisualizer';

describe('PromptVisualizer', () => {
    const stage = STARTER_RECIPES[0].stages[0];

    it('previews the single stage as a template and requests live data on demand', () => {
        const onPreviewLiveData = vi.fn();
        render(
            <PromptVisualizer
                stage={stage}
                previewState={{ status: 'template' }}
                onPreviewLiveData={onPreviewLiveData}
            />,
        );

        expect(screen.getByText('Template Preview')).toBeInTheDocument();
        expect(screen.getByText(/Analyze the injected news catalysts/)).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Preview Live Data' }));
        expect(onPreviewLiveData).toHaveBeenCalledTimes(1);
    });

    it('shows hydrated news in place of the placeholder once live data is loaded', () => {
        render(
            <PromptVisualizer
                stage={stage}
                previewState={{
                    status: 'hydrated',
                    hydratedByBlockId: { 'blk-news-1': '[News (live)]:\n- Live headline' },
                }}
                onPreviewLiveData={vi.fn()}
            />,
        );

        expect(screen.getByText('Live DB Hydrated')).toBeInTheDocument();
        expect(screen.getByText(/Live headline/)).toBeInTheDocument();
    });
});
