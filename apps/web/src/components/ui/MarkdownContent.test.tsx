import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { InlineMarkdown, MarkdownContent } from './MarkdownContent';

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

    it('renders mixed blocks containing a bold lead-in followed by bullet list items', () => {
        const mixedMarkdown = `**Critical levels:**
- SPX: 7,600 pivot
- 10Y: 5.05% resistance`;

        render(<MarkdownContent content={mixedMarkdown} />);

        const boldHeader = screen.getByText('Critical levels:');
        expect(boldHeader.tagName).toBe('STRONG');

        const bullet1 = screen.getByText('SPX: 7,600 pivot');
        expect(bullet1.tagName).toBe('LI');

        const bullet2 = screen.getByText('10Y: 5.05% resistance');
        expect(bullet2.tagName).toBe('LI');
    });

    it('renders ordered lists with parentheses and bolding', () => {
        const orderedMarkdown = `**1)** First trade setup
**2)** Second trade setup`;

        render(<MarkdownContent content={orderedMarkdown} />);

        const item1 = screen.getByText('First trade setup');
        expect(item1.tagName).toBe('LI');
        const item2 = screen.getByText('Second trade setup');
        expect(item2.tagName).toBe('LI');
    });

    it('renders horizontal rules, soft line breaks and lists directly after paragraph lines', () => {
        const md = `Positioning summary
- **No strong edge** for a new trade
- Waiting for VWAP

---

### Historical Precedents`;
        const { container } = render(<MarkdownContent content={md} />);
        expect(container.querySelector('hr')).toBeInTheDocument();
        expect(screen.getByText('No strong edge').tagName).toBe('STRONG');
        expect(screen.getAllByRole('listitem')).toHaveLength(2);
        expect(
            screen.getByRole('heading', { level: 3, name: 'Historical Precedents' }),
        ).toBeInTheDocument();
        expect(container.textContent).not.toContain('**');
        expect(container.textContent).not.toContain('###');
    });

    it('renders a table with bold cells that follows a paragraph line without a blank line', () => {
        const md = `Two shocks flagged (10/10):
| Catalyst | Impact |
|----------|--------|
| **NATO-Iran Escalation** | BEARISH |
| **Hormuz Shock** | BULLISH |`;
        const { container } = render(<MarkdownContent content={md} />);
        expect(container.querySelector('table')).toBeInTheDocument();
        expect(screen.getByText('NATO-Iran Escalation').tagName).toBe('STRONG');
        expect(screen.getAllByRole('row')).toHaveLength(3);
        expect(container.textContent).not.toContain('|');
    });

    it('renders fenced code blocks verbatim', () => {
        const md = '```\nconst a = **1**;\nconst b = 2;\n```';
        const { container } = render(<MarkdownContent content={md} />);
        const pre = container.querySelector('pre');
        expect(pre).toBeInTheDocument();
        expect(pre?.textContent).toBe('const a = **1**;\nconst b = 2;');
    });

    it('renders nested lists', () => {
        const md = '- Parent\n  - Child A\n  - Child B\n- Sibling';
        const { container } = render(<MarkdownContent content={md} />);
        expect(container.querySelectorAll('ul ul')).toHaveLength(1);
        expect(screen.getAllByRole('listitem')).toHaveLength(4);
    });

    it('strips unsafe link protocols', () => {
        render(<MarkdownContent content="[bad](javascript:alert(1)) and [ok](https://x.com)" />);
        expect(screen.queryByRole('link', { name: 'bad' })).not.toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'ok' })).toHaveAttribute('href', 'https://x.com');
    });

    it('does not warn about duplicate keys for repeated list items', () => {
        const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
        render(<MarkdownContent content={'- same\n- same\n- same'} />);
        expect(spy).not.toHaveBeenCalled();
        spy.mockRestore();
    });
});

describe('InlineMarkdown', () => {
    it('renders double underscores as bold and single underscores as italic', () => {
        render(
            <div data-testid="container">
                <InlineMarkdown text="This is __bold__ and _italic_ with ticker_symbol_name unchanged." />
            </div>,
        );

        const bold = screen.getByText('bold');
        expect(bold.tagName).toBe('STRONG');

        const italic = screen.getByText('italic');
        expect(italic.tagName).toBe('EM');

        expect(screen.getByText(/with ticker_symbol_name unchanged\./)).toBeInTheDocument();
    });

    it('renders bold and italic combined', () => {
        render(
            <div data-testid="container">
                <InlineMarkdown text="Prefix ***bold and italic*** suffix" />
            </div>,
        );

        const strong = screen.getByText('bold and italic');
        expect(strong.closest('strong')).toBeInTheDocument();
        expect(strong.closest('em')).toBeInTheDocument();
    });
});
