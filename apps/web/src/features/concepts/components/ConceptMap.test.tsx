import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { type Concept, ConceptMap } from './ConceptMap';

describe('ConceptMap (Tabbed Table)', () => {
    const mockData: Concept[] = [
        {
            id: '1',
            concept_name: 'Inflationary Shock',
            pca_x: 0.5,
            pca_y: 0.5,
            mention_count: 50,
            velocity_score: 2.5,
            first_mention_at: '2024-01-01T12:00:00Z',
            last_mention_at: '2024-01-15T12:00:00Z',
        },
        {
            id: '2',
            concept_name: 'Generative AI',
            pca_x: -0.5,
            pca_y: -0.5,
            mention_count: 120,
            velocity_score: 5.8,
            first_mention_at: '2024-02-10T12:00:00Z',
            last_mention_at: '2024-05-20T12:00:00Z',
        },
        {
            id: '3',
            concept_name: 'Quantum Computing',
            pca_x: 0.1,
            pca_y: -0.2,
            mention_count: 10,
            velocity_score: 0.5,
            first_mention_at: '2024-06-01T12:00:00Z',
            last_mention_at: '2024-06-02T12:00:00Z',
        },
    ];

    it('renders the search input and tab controls', () => {
        render(<ConceptMap data={mockData} />);

        expect(screen.getByPlaceholderText(/search concepts/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /trending/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /most mentioned/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /newest/i })).toBeInTheDocument();
    });

    it('filters rows based on search input', () => {
        render(<ConceptMap data={mockData} />);

        // Initially, all 3 are visible
        expect(screen.getByText('Inflationary Shock')).toBeInTheDocument();
        expect(screen.getByText('Generative AI')).toBeInTheDocument();
        expect(screen.getByText('Quantum Computing')).toBeInTheDocument();

        // Search for 'AI'
        const searchInput = screen.getByPlaceholderText(/search concepts/i);
        fireEvent.change(searchInput, { target: { value: 'AI' } });

        expect(screen.queryByText('Inflationary Shock')).not.toBeInTheDocument();
        expect(screen.getByText('Generative AI')).toBeInTheDocument();
        expect(screen.queryByText('Quantum Computing')).not.toBeInTheDocument();
    });

    it('orders data correctly when tabs are clicked', () => {
        render(<ConceptMap data={mockData} />);

        // "Trending" is default tab: sorted by velocity_score desc (Generative AI (5.8) -> Inflationary Shock (2.5) -> Quantum Computing (0.5))
        const rowsBefore = screen.getAllByRole('row');
        // Index 0 is header row. Rows are index 1, 2, 3
        expect(rowsBefore[1]).toHaveTextContent('Generative AI');
        expect(rowsBefore[2]).toHaveTextContent('Inflationary Shock');
        expect(rowsBefore[3]).toHaveTextContent('Quantum Computing');

        // Click "Most Mentioned" tab: sorted by mention_count desc (Generative AI (120) -> Inflationary Shock (50) -> Quantum Computing (10))
        const mostMentionedTab = screen.getByRole('button', { name: /most mentioned/i });
        fireEvent.click(mostMentionedTab);

        const rowsMentioned = screen.getAllByRole('row');
        expect(rowsMentioned[1]).toHaveTextContent('Generative AI');
        expect(rowsMentioned[2]).toHaveTextContent('Inflationary Shock');
        expect(rowsMentioned[3]).toHaveTextContent('Quantum Computing');

        // Click "Newest" tab: sorted by first_mention_at desc (Quantum Computing (June) -> Generative AI (Feb) -> Inflationary Shock (Jan))
        const newestTab = screen.getByRole('button', { name: /newest/i });
        fireEvent.click(newestTab);

        const rowsNewest = screen.getAllByRole('row');
        expect(rowsNewest[1]).toHaveTextContent('Quantum Computing');
        expect(rowsNewest[2]).toHaveTextContent('Generative AI');
        expect(rowsNewest[3]).toHaveTextContent('Inflationary Shock');
    });

    it('expands row details when row is clicked', () => {
        render(<ConceptMap data={mockData} />);

        // Details are not visible initially
        expect(screen.queryByText(/first seen:/i)).not.toBeInTheDocument();

        // Click on the Inflationary Shock row
        const rowHeader = screen.getByText('Inflationary Shock');
        fireEvent.click(rowHeader);

        // Details should expand
        expect(screen.getByText(/first seen:/i)).toBeInTheDocument();
        expect(screen.getByText(/last seen:/i)).toBeInTheDocument();
        expect(screen.getByText(/duration active:/i)).toBeInTheDocument();
    });
});
