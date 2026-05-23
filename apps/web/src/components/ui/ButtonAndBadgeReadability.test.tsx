import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

describe('Button and Badge Contrast/Readability Tests', () => {
    describe('Button Solid Contrast', () => {
        it('should use text-white for accent solid button', () => {
            const { getByRole } = render(
                <Button variant="solid" colorScheme="accent">
                    Accent Solid
                </Button>,
            );
            const button = getByRole('button');
            expect(button.className).toContain('text-white');
            expect(button.className).not.toContain('text-zinc-950');
        });

        it('should use text-white for danger solid button', () => {
            const { getByRole } = render(
                <Button variant="solid" colorScheme="danger">
                    Danger Solid
                </Button>,
            );
            const button = getByRole('button');
            expect(button.className).toContain('text-white');
            expect(button.className).not.toContain('text-zinc-950');
        });

        it('should use text-white for info solid button', () => {
            const { getByRole } = render(
                <Button variant="solid" colorScheme="info">
                    Info Solid
                </Button>,
            );
            const button = getByRole('button');
            expect(button.className).toContain('text-white');
            expect(button.className).not.toContain('text-zinc-950');
        });

        it('should use text-zinc-950 for success solid button', () => {
            const { getByRole } = render(
                <Button variant="solid" colorScheme="success">
                    Success Solid
                </Button>,
            );
            const button = getByRole('button');
            expect(button.className).toContain('text-zinc-950');
            expect(button.className).not.toContain('text-white');
        });

        it('should use text-zinc-950 for warning solid button', () => {
            const { getByRole } = render(
                <Button variant="solid" colorScheme="warning">
                    Warning Solid
                </Button>,
            );
            const button = getByRole('button');
            expect(button.className).toContain('text-zinc-950');
            expect(button.className).not.toContain('text-white');
        });
    });

    describe('Badge Solid Contrast', () => {
        it('should use text-white for accent solid badge', () => {
            const { getByText } = render(
                <Badge variant="solid" colorScheme="accent">
                    Accent Solid Badge
                </Badge>,
            );
            const badge = getByText('Accent Solid Badge');
            expect(badge.className).toContain('text-white');
            expect(badge.className).not.toContain('text-zinc-950');
        });

        it('should use text-white for danger solid badge', () => {
            const { getByText } = render(
                <Badge variant="solid" colorScheme="danger">
                    Danger Solid Badge
                </Badge>,
            );
            const badge = getByText('Danger Solid Badge');
            expect(badge.className).toContain('text-white');
            expect(badge.className).not.toContain('text-zinc-950');
        });

        it('should use text-white for info solid badge', () => {
            const { getByText } = render(
                <Badge variant="solid" colorScheme="info">
                    Info Solid Badge
                </Badge>,
            );
            const badge = getByText('Info Solid Badge');
            expect(badge.className).toContain('text-white');
            expect(badge.className).not.toContain('text-zinc-950');
        });

        it('should use text-zinc-950 for success solid badge', () => {
            const { getByText } = render(
                <Badge variant="solid" colorScheme="success">
                    Success Solid Badge
                </Badge>,
            );
            const badge = getByText('Success Solid Badge');
            expect(badge.className).toContain('text-zinc-950');
            expect(badge.className).not.toContain('text-white');
        });

        it('should use text-zinc-950 for warning solid badge', () => {
            const { getByText } = render(
                <Badge variant="solid" colorScheme="warning">
                    Warning Solid Badge
                </Badge>,
            );
            const badge = getByText('Warning Solid Badge');
            expect(badge.className).toContain('text-zinc-950');
            expect(badge.className).not.toContain('text-white');
        });

        it('should use text-white for medium severity solid badge', () => {
            const { getByText } = render(
                <Badge variant="solid" severity="medium">
                    Medium Solid Badge
                </Badge>,
            );
            const badge = getByText('Medium Solid Badge');
            expect(badge.className).toContain('text-white');
            expect(badge.className).not.toContain('text-zinc-950');
        });

        it('should use text-zinc-950 for high severity solid badge', () => {
            const { getByText } = render(
                <Badge variant="solid" severity="high">
                    High Solid Badge
                </Badge>,
            );
            const badge = getByText('High Solid Badge');
            expect(badge.className).toContain('text-zinc-950');
            expect(badge.className).not.toContain('text-white');
        });
    });

    describe('Unified Component Colors (No Light/Dark Distinction)', () => {
        it('should use translucent styling directly for success soft badge without dark prefix', () => {
            const { getByText } = render(
                <Badge variant="soft" colorScheme="success">
                    Success Soft Badge
                </Badge>,
            );
            const badge = getByText('Success Soft Badge');
            expect(badge.className).toContain('bg-success/20');
            expect(badge.className).toContain('text-success');
            expect(badge.className).not.toContain('bg-success-light');
            expect(badge.className).not.toContain('text-success-dark');
        });

        it('should use translucent styling directly for accent soft badge without dark prefix', () => {
            const { getByText } = render(
                <Badge variant="soft" colorScheme="accent">
                    Accent Soft Badge
                </Badge>,
            );
            const badge = getByText('Accent Soft Badge');
            expect(badge.className).toContain('bg-accent/20');
            expect(badge.className).toContain('text-accent');
            expect(badge.className).not.toContain('bg-accent-light');
            expect(badge.className).not.toContain('text-accent-dark');
        });

        it('should use translucent styling directly for success soft button without dark prefix', () => {
            const { getByRole } = render(
                <Button variant="soft" colorScheme="success">
                    Success Soft Button
                </Button>,
            );
            const button = getByRole('button');
            expect(button.className).toContain('bg-success/20');
            expect(button.className).toContain('text-success');
            expect(button.className).not.toContain('bg-success-light');
            expect(button.className).not.toContain('text-success-dark');
        });
    });
});
