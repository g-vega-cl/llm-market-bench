import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Route } from './how-it-works';

// Mock the JSON import to simulate dynamic phase description loading
vi.mock('~/config/how-it-works.json', () => ({
    default: [
        {
            phase: 1,
            title: 'Mocked Ingestion Phase',
            badge: 'Mocked Ingestion Badge',
            description: 'This is the mocked description for Ingestion.',
            bullets: ['Mocked Ingestion Bullet 1', 'Mocked Ingestion Bullet 2'],
            tags: ['Mock Tag 1', 'Mock Tag 2'],
            icon: '📰',
        },
        {
            phase: 2,
            title: 'Mocked Pre-Analysis Phase',
            badge: 'Mocked Pre-Analysis Badge',
            description: 'This is the mocked description for Pre-Analysis.',
            bullets: ['Mocked Pre-Analysis Bullet 1'],
            tags: ['Mock Tag 3'],
            icon: '⚙',
        },
    ],
}));

describe('HowItWorks Component dynamic rendering', () => {
    it('renders phases dynamically from the compiled JSON file', () => {
        const HowItWorksComponent = Route.options.component;
        if (!HowItWorksComponent) {
            throw new Error('Component not defined on Route');
        }

        render(<HowItWorksComponent />);

        // Check for mock data titles and descriptions
        expect(screen.getByText('Mocked Ingestion Phase')).toBeInTheDocument();
        expect(screen.getByText('Mocked Ingestion Badge')).toBeInTheDocument();
        expect(
            screen.getByText('This is the mocked description for Ingestion.'),
        ).toBeInTheDocument();
        expect(screen.getByText('Mocked Ingestion Bullet 1')).toBeInTheDocument();
        expect(screen.getByText('Mock Tag 1')).toBeInTheDocument();

        expect(screen.getByText('Mocked Pre-Analysis Phase')).toBeInTheDocument();
        expect(screen.getByText('Mocked Pre-Analysis Badge')).toBeInTheDocument();
        expect(
            screen.getByText('This is the mocked description for Pre-Analysis.'),
        ).toBeInTheDocument();
    });
});
