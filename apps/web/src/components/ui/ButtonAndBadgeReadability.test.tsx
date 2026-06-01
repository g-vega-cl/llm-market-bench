import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

describe('Button and Badge Contrast Compliance (A11y Checks)', () => {
    it('verifies neutral ghost Button uses responsive high-contrast classes instead of hardcoded zinc-100', () => {
        const { container } = render(
            <Button colorScheme="neutral" variant="ghost">
                Test Ghost
            </Button>,
        );
        const button = container.querySelector('button');
        expect(button).toBeInTheDocument();
        // Check for light-mode text contrast and dark-mode text contrast
        expect(button?.className).toContain('text-zinc-900');
        expect(button?.className).toContain('dark:text-zinc-100');
        expect(button?.className).toContain('hover:bg-zinc-100');
        expect(button?.className).toContain('dark:hover:bg-zinc-800');
    });

    it('verifies neutral outline Button uses responsive high-contrast border and text classes', () => {
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
});
