import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MarkdownContent } from './MarkdownContent';

describe('MarkdownContent', () => {
    it('renders headings correctly', () => {
        render(<MarkdownContent content={'# Heading 1\n\n## Heading 2\n\n### Heading 3'} />);
        expect(screen.getByRole('heading', { level: 1, name: 'Heading 1' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { level: 2, name: 'Heading 2' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { level: 3, name: 'Heading 3' })).toBeInTheDocument();
    });

    it('renders lists, bold, italics, links, blockquotes, and code', () => {
        const sampleMarkdown = `
- Bullet item 1
- Bullet item 2

1. Ordered 1

**Strong text** and *italic text*

> A famous market quote

[Market Link](https://example.com)

\`console.log('code')\`
`;

        render(<MarkdownContent content={sampleMarkdown} />);

        expect(screen.getByText('Bullet item 1')).toBeInTheDocument();
        expect(screen.getByText('Ordered 1')).toBeInTheDocument();

        const strong = screen.getByText('Strong text');
        expect(strong.tagName).toBe('STRONG');

        const italic = screen.getByText('italic text');
        expect(italic.tagName).toBe('EM');

        expect(screen.getByText('A famous market quote')).toBeInTheDocument();

        const link = screen.getByRole('link', { name: 'Market Link' });
        expect(link).toHaveAttribute('href', 'https://example.com');
        expect(link).toHaveAttribute('target', '_blank');

        expect(screen.getByText("console.log('code')")).toBeInTheDocument();
    });

    it('renders tables properly', () => {
        const tableMarkdown = `
| Ticker | Price | Change |
| ------ | ----- | ------ |
| AAPL   | 220   | +1.5%  |
`;

        render(<MarkdownContent content={tableMarkdown} />);

        expect(screen.getByText('Ticker')).toBeInTheDocument();
        expect(screen.getByText('AAPL')).toBeInTheDocument();
        expect(screen.getByText('+1.5%')).toBeInTheDocument();
    });
});
