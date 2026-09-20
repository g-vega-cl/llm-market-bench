import type React from 'react';

interface MarkdownContentProps {
    content: string;
    className?: string;
}

export interface InlineMarkdownProps {
    text?: string | null;
    className?: string;
}

function renderTokenNode(fullMatch: string, key: string): React.ReactNode {
    if (fullMatch.startsWith('***') || fullMatch.startsWith('___')) {
        const inner = fullMatch.slice(3, -3);
        return (
            <strong key={key} className="font-semibold text-zinc-900 dark:text-white">
                <em className="italic text-zinc-800 dark:text-zinc-200">
                    {parseInlineMarkdown(inner)}
                </em>
            </strong>
        );
    }
    if (fullMatch.startsWith('**') || fullMatch.startsWith('__')) {
        const inner = fullMatch.slice(2, -2);
        return (
            <strong key={key} className="font-semibold text-zinc-900 dark:text-white">
                {parseInlineMarkdown(inner)}
            </strong>
        );
    }
    if (fullMatch.startsWith('*') || fullMatch.startsWith('_')) {
        const inner = fullMatch.slice(1, -1);
        return (
            <em key={key} className="italic text-zinc-800 dark:text-zinc-200">
                {parseInlineMarkdown(inner)}
            </em>
        );
    }
    if (fullMatch.startsWith('`')) {
        const inner = fullMatch.slice(1, -1);
        return (
            <code
                key={key}
                className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-electric-blue-600 dark:text-electric-blue-400 font-mono text-xs"
            >
                {inner}
            </code>
        );
    }
    if (fullMatch.startsWith('[')) {
        const linkMatch = fullMatch.match(/^\[(.*?)\]\((.*?)\)$/);
        const linkText = linkMatch?.[1] || '';
        const url = linkMatch?.[2] || '';
        return (
            <a
                key={key}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-electric-blue-500 hover:text-electric-blue-600 underline font-medium"
            >
                {linkText}
            </a>
        );
    }
    return fullMatch;
}

/**
 * Parses inline markdown tokens (**bold**, __bold__, *italic*, _italic_, `code`, [link](url)) into React nodes.
 */
export function parseInlineMarkdown(text: string): React.ReactNode[] {
    if (!text) return [];
    const nodes: React.ReactNode[] = [];
    let keyIndex = 0;

    // Pattern matches: ***bold italic***, ___bold italic___, **bold**, __bold__, *italic*, _italic_, `code`, [link](url)
    const regex =
        /(\*\*\*(.*?)\*\*\*|___(.*?)___|\*\*(.*?)\*\*|__(.*?)__|\*(.*?)\*|(?<!\w)_(.*?)_(?!\w)|`(.*?)`|\[(.*?)\]\((.*?)\))/g;
    let match: RegExpExecArray | null;
    let lastIndex = 0;

    regex.lastIndex = 0;

    // biome-ignore lint/suspicious/noAssignInExpressions: standard regex match loop
    while ((match = regex.exec(text)) !== null) {
        if (match.index > lastIndex) {
            nodes.push(text.substring(lastIndex, match.index));
        }

        nodes.push(renderTokenNode(match[0], `tok-${keyIndex++}`));
        lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
        nodes.push(text.substring(lastIndex));
    }

    return nodes.length > 0 ? nodes : [text];
}

export function InlineMarkdown({ text, className = '' }: InlineMarkdownProps) {
    if (!text) return null;
    const parsed = parseInlineMarkdown(text);
    if (className) {
        return <span className={className}>{parsed}</span>;
    }
    return <>{parsed}</>;
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

function isUnorderedLine(line: string): boolean {
    return /^\s*[-*•]\s+/.test(line);
}

function isOrderedLine(line: string): boolean {
    return /^\s*(\d+[.)]|\*\*\d+[.)]\*\*)\s+/.test(line);
}

function renderUnorderedList(lines: string[], blockKey: string): React.ReactNode {
    return (
        <ul
            key={blockKey}
            className="list-disc list-inside space-y-1.5 my-3 text-sm text-zinc-700 dark:text-zinc-300 pl-2"
        >
            {lines.map((l) => {
                const cleanText = l.replace(/^\s*[-*•]\s+/, '');
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

function renderOrderedList(lines: string[], blockKey: string): React.ReactNode {
    return (
        <ol
            key={blockKey}
            className="list-decimal list-inside space-y-1.5 my-3 text-sm text-zinc-700 dark:text-zinc-300 pl-2"
        >
            {lines.map((l) => {
                const cleanText = l.replace(/^\s*(\d+[.)]|\*\*\d+[.)]\*\*)\s+/, '');
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

function renderList(lines: string[], blockKey: string): React.ReactNode | null {
    if (lines.every(isUnorderedLine)) {
        return renderUnorderedList(lines, blockKey);
    }
    if (lines.every(isOrderedLine)) {
        return renderOrderedList(lines, blockKey);
    }
    return null;
}

function renderBlockquote(trimmed: string, blockKey: string): React.ReactNode {
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

function renderMixedListBlock(lines: string[], blockKey: string): React.ReactNode {
    const groups: { kind: 'unordered' | 'ordered' | 'text'; lines: string[] }[] = [];
    for (const line of lines) {
        const kind = isUnorderedLine(line) ? 'unordered' : isOrderedLine(line) ? 'ordered' : 'text';
        const lastGroup = groups[groups.length - 1];
        if (lastGroup && lastGroup.kind === kind) {
            lastGroup.lines.push(line);
        } else {
            groups.push({ kind, lines: [line] });
        }
    }

    return (
        <div key={blockKey} className="space-y-2">
            {groups.map((group) => {
                const firstLine = group.lines[0]?.slice(0, 16) || 'group';
                const groupKey = `${blockKey}-${group.kind}-${firstLine}`;
                if (group.kind === 'unordered') {
                    return renderUnorderedList(group.lines, groupKey);
                }
                if (group.kind === 'ordered') {
                    return renderOrderedList(group.lines, groupKey);
                }
                const textContent = group.lines.join(' ').trim();
                return (
                    <p
                        key={groupKey}
                        className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed font-light"
                    >
                        {parseInlineMarkdown(textContent)}
                    </p>
                );
            })}
        </div>
    );
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
        return renderBlockquote(trimmed, blockKey);
    }

    const lines = trimmed.split('\n');
    const list = renderList(lines, blockKey);
    if (list) return list;

    const table = renderTable(lines, trimmed, blockKey);
    if (table) return table;

    if (lines.some((l) => isUnorderedLine(l) || isOrderedLine(l))) {
        return renderMixedListBlock(lines, blockKey);
    }

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
