import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { type Concept, ConceptMap } from './ConceptMap';

// Mock the Link component from TanStack Router to prevent routing failures in tests
vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        params,
    }: {
        children: React.ReactNode;
        to: string;
        params?: Record<string, unknown>;
    }) => {
        const path = to.replace('$memoryId', (params?.memoryId as string) || '');
        return <a href={path}>{children}</a>;
    },
}));

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

    const mockFetchMemoriesFn = vi.fn().mockResolvedValue([
        {
            id: 'memory-101',
            content:
                'MARKET EVENT: May 2026 US PPI Surge [ONGOING] | IMPACT: BEARISH | SUMMARY: A surprising 1.4% m/m US PPI surge',
            metadata: { impact: 'BEARISH' },
            similarity: 0.85,
            created_at: '2026-05-24T12:00:00Z',
        },
    ]);

    const createTestQueryClient = () =>
        new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false,
                },
            },
        });

    const renderWithQueryClient = (ui: React.ReactElement) => {
        const queryClient = createTestQueryClient();
        return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
    };

    it('renders the search input and tab controls', () => {
        renderWithQueryClient(<ConceptMap data={mockData} fetchMemoriesFn={mockFetchMemoriesFn} />);

        expect(screen.getByPlaceholderText(/search concepts/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /trending/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /most mentioned/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /newest/i })).toBeInTheDocument();
    });

    it('filters rows based on search input', () => {
        renderWithQueryClient(<ConceptMap data={mockData} fetchMemoriesFn={mockFetchMemoriesFn} />);

        // Initially, all 3 are visible
        expect(screen.getAllByText('Inflationary Shock')[0]).toBeInTheDocument();
        expect(screen.getAllByText('Generative AI')[0]).toBeInTheDocument();
        expect(screen.getAllByText('Quantum Computing')[0]).toBeInTheDocument();

        // Search for 'AI'
        const searchInput = screen.getByPlaceholderText(/search concepts/i);
        fireEvent.change(searchInput, { target: { value: 'AI' } });

        expect(screen.queryByText('Inflationary Shock')).not.toBeInTheDocument();
        expect(screen.getAllByText('Generative AI')[0]).toBeInTheDocument();
        expect(screen.queryByText('Quantum Computing')).not.toBeInTheDocument();
    });

    it('orders data correctly when tabs are clicked', () => {
        renderWithQueryClient(<ConceptMap data={mockData} fetchMemoriesFn={mockFetchMemoriesFn} />);

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

    it('expands row details when row is clicked', async () => {
        renderWithQueryClient(<ConceptMap data={mockData} fetchMemoriesFn={mockFetchMemoriesFn} />);

        // Details are not visible initially
        expect(screen.queryByText(/first seen:/i)).not.toBeInTheDocument();

        // Click on the Inflationary Shock row
        const rowHeader = screen.getAllByText('Inflationary Shock')[0];
        fireEvent.click(rowHeader);

        // Details should expand
        expect(screen.getAllByText(/first seen:/i)[0]).toBeInTheDocument();
        expect(screen.getAllByText(/last seen:/i)[0]).toBeInTheDocument();
        expect(screen.getAllByText(/duration active:/i)[0]).toBeInTheDocument();
    });

    it('fetches and renders related memories with date when row is expanded', async () => {
        renderWithQueryClient(<ConceptMap data={mockData} fetchMemoriesFn={mockFetchMemoriesFn} />);

        // Click on the Inflationary Shock row
        const rowHeader = screen.getAllByText('Inflationary Shock')[0];
        fireEvent.click(rowHeader);

        // Verify that loading state or resolved state is shown
        expect(screen.getAllByText(/loading related memories/i)[0]).toBeInTheDocument();

        // Wait for memories to load
        const memoryContent = await screen.findAllByText(/MARKET EVENT: May 2026 US PPI Surge/);
        expect(memoryContent[0]).toBeInTheDocument();
        expect(screen.getAllByText('85% Match')[0]).toBeInTheDocument();
        expect(screen.getAllByText('BEARISH')[0]).toBeInTheDocument();
        expect(screen.getAllByText('May 24, 2026')[0]).toBeInTheDocument();

        // Verify the event chain link
        const link = screen.getAllByRole('link', { name: /view event chain/i })[0];
        expect(link).toHaveAttribute('href', '/memories/chain/memory-101');
    });

    it('renders mobile cards with concept metrics', () => {
        renderWithQueryClient(<ConceptMap data={mockData} fetchMemoriesFn={mockFetchMemoriesFn} />);

        const mobileCard = screen.getByTestId('mobile-concept-card-1');
        expect(mobileCard).toBeInTheDocument();
        expect(mobileCard).toHaveTextContent('Inflationary Shock');
        expect(mobileCard).toHaveTextContent('Mentions: 50');
        expect(mobileCard).toHaveTextContent('Velocity: 2.50');
    });
});
