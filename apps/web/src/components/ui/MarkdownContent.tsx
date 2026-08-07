import type React from 'react';

interface MarkdownContentProps {
    content: string;
    className?: string;
}

/**
 * Parses inline markdown tokens (**bold**, *italic*, `code`, [link](url)) into React nodes.
 */
function parseInlineMarkdown(text: string): React.ReactNode[] {
    const nodes: React.ReactNode[] = [];
    let keyIndex = 0;

    // Pattern matches: **bold**, *italic*, `code`, [link](url)
    const regex = /(\*\*(.*?)\*\*|\*(.*?)\*|`(.*?)`|\[(.*?)\]\((.*?)\))/g;
    let match: RegExpExecArray | null;
    let lastIndex = 0;

    regex.lastIndex = 0;

    // biome-ignore lint/suspicious/noAssignInExpressions: standard regex match loop
    while ((match = regex.exec(text)) !== null) {
        if (match.index > lastIndex) {
            nodes.push(text.substring(lastIndex, match.index));
        }

        const fullMatch = match[0];
        if (fullMatch.startsWith('**')) {
            const inner = match[2];
            nodes.push(
                <strong
                    key={`bold-${keyIndex++}`}
                    className="font-semibold text-zinc-900 dark:text-white"
                >
                    {parseInlineMarkdown(inner)}
                </strong>,
            );
        } else if (fullMatch.startsWith('*')) {
            const inner = match[3];
            nodes.push(
                <em
                    key={`italic-${keyIndex++}`}
                    className="italic text-zinc-800 dark:text-zinc-200"
                >
                    {parseInlineMarkdown(inner)}
                </em>,
            );
        } else if (fullMatch.startsWith('`')) {
            const inner = match[4];
            nodes.push(
                <code
                    key={`code-${keyIndex++}`}
                    className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-electric-blue-600 dark:text-electric-blue-400 font-mono text-xs"
                >
                    {inner}
                </code>,
            );
        } else if (fullMatch.startsWith('[')) {
            const linkText = match[5];
            const url = match[6];
            nodes.push(
                <a
                    key={`link-${keyIndex++}`}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-electric-blue-500 hover:text-electric-blue-600 underline font-medium"
                >
                    {linkText}
                </a>,
            );
        }

        lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
        nodes.push(text.substring(lastIndex));
    }

    return nodes.length > 0 ? nodes : [text];
}

function renderHeading(trimmed: string, blockKey: string): React.ReactNode | null {
    const match = trimmed.match(/^(#{1,4})\s+(.+)$/s);
    if (!match) return null;

    const level = match[1].length;
    const children = parseInlineMarkdown(match[2]);

    if (level === 1) {
        return (
            <h1
                key={blockKey}
                className="text-xl md:text-2xl font-black text-zinc-900 dark:text-white mt-6 mb-3 first:mt-0 tracking-tight"
            >
                {children}
            </h1>
        );
    }
    if (level === 2) {
        return (
            <h2
                key={blockKey}
                className="text-lg md:text-xl font-bold text-zinc-900 dark:text-white mt-5 mb-2.5 first:mt-0 tracking-tight border-b border-zinc-200/60 dark:border-zinc-800/60 pb-1"
            >
                {children}
            </h2>
        );
    }
    if (level === 3) {
        return (
            <h3
                key={blockKey}
                className="text-base md:text-lg font-bold text-zinc-900 dark:text-white mt-4 mb-2 first:mt-0 tracking-tight"
            >
                {children}
            </h3>
        );
    }
    return (
        <h4
            key={blockKey}
            className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mt-3 mb-1.5 first:mt-0"
        >
            {children}
        </h4>
    );
}

function renderList(lines: string[], blockKey: string): React.ReactNode | null {
    const isUnordered = lines.every((l) => /^\s*[-*]\s+/.test(l));
    if (isUnordered) {
        return (
            <ul
                key={blockKey}
                className="list-disc list-inside space-y-1.5 my-3 text-sm text-zinc-700 dark:text-zinc-300 pl-2"
            >
                {lines.map((l) => {
                    const cleanText = l.replace(/^\s*[-*]\s+/, '');
                    return (
                        <li
                            key={`ul-${cleanText}`}
                            className="leading-relaxed marker:text-electric-blue-500 font-light"
                        >
                            {parseInlineMarkdown(cleanText)}
                        </li>
                    );
                })}
            </ul>
        );
    }

    const isOrdered = lines.every((l) => /^\s*\d+\.\s+/.test(l));
    if (isOrdered) {
        return (
            <ol
                key={blockKey}
                className="list-decimal list-inside space-y-1.5 my-3 text-sm text-zinc-700 dark:text-zinc-300 pl-2"
            >
                {lines.map((l) => {
                    const cleanText = l.replace(/^\s*\d+\.\s+/, '');
                    return (
                        <li
                            key={`ol-${cleanText}`}
                            className="leading-relaxed marker:text-electric-blue-500 font-light"
                        >
                            {parseInlineMarkdown(cleanText)}
                        </li>
                    );
                })}
            </ol>
        );
    }

    return null;
}

function renderTable(lines: string[], trimmed: string, blockKey: string): React.ReactNode | null {
    if (!trimmed.includes('|') || lines.length < 2 || !lines[1].includes('---')) {
        return null;
    }

    const parseRow = (rowStr: string) =>
        rowStr
            .split('|')
            .slice(1, -1)
            .map((cell) => cell.trim());

    const headers = parseRow(lines[0]);
    const rows = lines.slice(2).map(parseRow);

    return (
        <div key={blockKey} className="overflow-x-auto my-4">
            <table className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-800 text-xs text-left border border-zinc-200 dark:border-zinc-800 rounded-lg">
                <thead>
                    <tr>
                        {headers.map((h) => (
                            <th
                                key={`th-${h}`}
                                className="px-3 py-2 bg-zinc-100 dark:bg-zinc-800 font-bold text-zinc-900 dark:text-white"
                            >
                                {parseInlineMarkdown(h)}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => {
                        const rowKey = `tr-${row.join('-')}`;
                        return (
                            <tr key={rowKey}>
                                {row.map((cell) => (
                                    <td
                                        key={`td-${cell}`}
                                        className="px-3 py-2 border-b border-zinc-100 dark:border-zinc-800/60 text-zinc-700 dark:text-zinc-300"
                                    >
                                        {parseInlineMarkdown(cell)}
                                    </td>
                                ))}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

function renderBlock(block: string, blockKey: string): React.ReactNode {
    const trimmed = block.trim();
    if (!trimmed) return null;

    if (trimmed.startsWith('#')) {
        const heading = renderHeading(trimmed, blockKey);
        if (heading) return heading;
    }

    if (trimmed.startsWith('>')) {
        const quoteText = trimmed
            .split('\n')
            .map((line) => line.replace(/^>\s?/, ''))
            .join('\n');
        return (
            <blockquote
                key={blockKey}
                className="border-l-4 border-electric-blue-500 pl-4 py-2 my-4 bg-electric-blue-50/40 dark:bg-electric-blue-950/20 text-zinc-700 dark:text-zinc-300 rounded-r-lg italic text-sm"
            >
                {parseInlineMarkdown(quoteText)}
            </blockquote>
        );
    }

    const lines = trimmed.split('\n');
    const list = renderList(lines, blockKey);
    if (list) return list;

    const table = renderTable(lines, trimmed, blockKey);
    if (table) return table;

    return (
        <p
            key={blockKey}
            className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed mb-4 last:mb-0 font-light"
        >
            {parseInlineMarkdown(trimmed)}
        </p>
    );
}

/**
 * Custom zero-dependency block & inline Markdown Renderer for React.
 */
export function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
    if (!content) return null;

    const blocks = content.trim().split(/\n\s*\n/);

    return (
        <div className={`space-y-3 ${className}`}>
            {blocks.map((block) => {
                const trimmed = block.trim();
                if (!trimmed) return null;
                const blockKey = `blk-${trimmed.slice(0, 16).replace(/[^a-zA-Z0-9]/g, '')}`;
                return renderBlock(block, blockKey);
            })}
        </div>
    );
}
