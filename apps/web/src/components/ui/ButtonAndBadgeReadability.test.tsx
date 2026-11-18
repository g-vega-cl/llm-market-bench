import { Badge, Button, Card, ConfidenceBar } from '@llm-market-bench/ui-design-system';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

describe('Button, Badge, Card, and ConfidenceBar Voxel Compliance', () => {
    it('verifies solid neutral Button uses voxel elevation classes', () => {
        const { container } = render(
            <Button colorScheme="neutral" variant="solid">
                Test Solid
            </Button>,
        );
        const button = container.querySelector('button');
        expect(button).toBeInTheDocument();
        expect(button?.className).toContain('bg-voxel-elevated');
        expect(button?.className).toContain('text-voxel-ink');
        expect(button?.className).toContain('hover:bg-voxel-surface');
        expect(button?.className).not.toContain('dark:');
    });

    it('verifies outline neutral Button uses a voxel bevel border and ink text', () => {
        const { container } = render(
            <Button colorScheme="neutral" variant="outline">
                Test Outline
            </Button>,
        );
        const button = container.querySelector('button');
        expect(button?.className).toContain('border-voxel-bevel-hi');
        expect(button?.className).toContain('text-voxel-ink');
        expect(button?.className).not.toContain('dark:');
    });

    it('verifies soft neutral Badge uses voxel surface and muted text', () => {
        const { container } = render(
            <Badge colorScheme="neutral" variant="soft">
                Normal
            </Badge>,
        );
        const badge = container.querySelector('span');
        expect(badge?.className).toContain('bg-voxel-surface');
        expect(badge?.className).toContain('text-voxel-muted');
        expect(badge?.className).not.toContain('dark:');
    });

    it('verifies Card defaults to sharp voxel geometry (rounded-none and voxel-card)', () => {
        const { container } = render(<Card>Voxel Block</Card>);
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
