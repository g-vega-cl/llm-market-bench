import { Badge, Button, Card, ConfidenceBar } from '@llm-market-bench/ui-design-system';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

describe('Button, Badge, Card, and ConfidenceBar Boxel Compliance', () => {
    it('verifies neutral ghost Button uses high-contrast classes', () => {
        const { container } = render(
            <Button colorScheme="neutral" variant="ghost">
                Test Ghost
            </Button>,
        );
        const button = container.querySelector('button');
        expect(button).toBeInTheDocument();
        expect(button?.className).toContain('text-zinc-900');
        expect(button?.className).toContain('dark:text-zinc-100');
        expect(button?.className).toContain('hover:bg-zinc-100');
        expect(button?.className).toContain('dark:hover:bg-zinc-800');
    });

    it('verifies neutral outline Button uses high-contrast border and text classes', () => {
        const { container } = render(
            <Button colorScheme="neutral" variant="outline">
                Test Outline
            </Button>,
        );
        const button = container.querySelector('button');
        expect(button?.className).toContain('border-zinc-300');
        expect(button?.className).toContain('dark:border-zinc-700');
        expect(button?.className).toContain('text-zinc-900');
        expect(button?.className).toContain('dark:text-zinc-100');
    });

    it('verifies neutral soft Button uses high-contrast background and text classes', () => {
        const { container } = render(
            <Button colorScheme="neutral" variant="soft">
                Test Soft
            </Button>,
        );
        const button = container.querySelector('button');
        expect(button?.className).toContain('bg-zinc-100');
        expect(button?.className).toContain('dark:bg-zinc-800');
        expect(button?.className).toContain('text-zinc-900');
        expect(button?.className).toContain('dark:text-zinc-100');
    });

    it('verifies neutral soft Badge uses high-contrast text zinc-600 and dark:zinc-400', () => {
        const { container } = render(
            <Badge colorScheme="neutral" variant="soft">
                Normal
            </Badge>,
        );
        const badge = container.querySelector('span');
        expect(badge?.className).toContain('text-zinc-600');
        expect(badge?.className).toContain('dark:text-zinc-400');
        expect(badge?.className).toContain('bg-zinc-100');
        expect(badge?.className).toContain('dark:bg-zinc-800/40');
    });

    it('verifies Card defaults to sharp boxel geometry (rounded-none and voxel-card)', () => {
        const { container } = render(<Card>Boxel Block</Card>);
        const card = container.firstElementChild;
        expect(card?.className).toContain('rounded-none');
        expect(card?.className).toContain('voxel-card');
    });

    it('verifies ConfidenceBar renders 10 discrete voxel segments', () => {
        render(<ConfidenceBar label="Confidence" value={76} />);
        const segments = screen.getAllByTestId('confidence-segment');
        expect(segments).toHaveLength(10);
        const filled = segments.filter((el) => el.getAttribute('data-filled') === 'true');
        expect(filled).toHaveLength(8);
        expect(screen.getByText('76%')).toBeInTheDocument();
    });
});
