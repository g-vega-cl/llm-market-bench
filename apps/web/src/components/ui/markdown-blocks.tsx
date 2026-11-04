import type React from 'react';
import { parseInlineMarkdown } from './markdown-inline';
import { type Block, type ListBlock, parseBlocks } from './markdown-parse';

export interface MarkdownContentProps {
    content: string;
    className?: string;
}

const TEXT = 'text-sm text-zinc-300 leading-relaxed font-light';

function renderList(list: ListBlock): React.ReactNode {
    const Tag = list.ordered ? 'ol' : 'ul';
    const style = list.ordered ? 'list-decimal' : 'list-disc';
    return (
        <Tag key={list.id} className={`${style} list-inside flex flex-col gap-1.5 ${TEXT} pl-2`}>
            {list.items.map((item) => (
                <li key={item.id} className="leading-relaxed marker:text-accent font-light">
                    {parseInlineMarkdown(item.text)}
                    {item.children.map(renderList)}
                </li>
            ))}
        </Tag>
    );
}

function renderHeading(level: number, text: string, key: string): React.ReactNode {
    const children = parseInlineMarkdown(text);
    if (level === 1) {
        return (
            <h1
                key={key}
                className="text-lg font-bold font-display uppercase tracking-wider text-white"
            >
                {children}
            </h1>
        );
    }
    if (level === 2) {
        return (
            <h2
                key={key}
                className="text-lg font-bold font-display uppercase tracking-wider text-white border-b border-zinc-800 pb-1"
            >
                {children}
            </h2>
        );
    }
    if (level === 3) {
        return (
            <h3 key={key} className="text-sm font-bold text-white tracking-tight">
                {children}
            </h3>
        );
    }
    return (
        <h4 key={key} className="text-xs font-bold text-zinc-300">
            {children}
        </h4>
    );
}

function renderTable(block: Extract<Block, { kind: 'table' }>): React.ReactNode {
    return (
        <div key={block.id} className="overflow-x-auto">
            <table className="min-w-full divide-y divide-zinc-800 text-xs font-normal text-left border border-zinc-800 rounded-none">
                <thead>
                    <tr>
                        {block.headers.map((h) => (
                            <th key={h.id} className="px-3 py-2 bg-zinc-800 font-bold text-white">
                                {parseInlineMarkdown(h.text)}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {block.rows.map((row) => (
                        <tr key={row.id}>
                            {row.cells.map((cell) => (
                                <td
                                    key={cell.id}
                                    className="px-3 py-2 border-b border-zinc-800/60 text-zinc-300"
                                >
                                    {parseInlineMarkdown(cell.text)}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function renderParagraph(block: Extract<Block, { kind: 'para' }>): React.ReactNode {
    const parts: React.ReactNode[] = [];
    let n = 0;
    for (const line of block.lines) {
        if (n > 0) parts.push(<br key={`${block.id}-br${n}`} />);
        parts.push(<span key={`${block.id}-l${n}`}>{parseInlineMarkdown(line)}</span>);
        n++;
    }
    return (
        <p key={block.id} className={TEXT}>
            {parts}
        </p>
    );
}

function renderBlock(block: Block): React.ReactNode {
    switch (block.kind) {
        case 'heading':
            return renderHeading(block.level, block.text, block.id);
        case 'hr':
            return <hr key={block.id} className="border-0 border-t border-zinc-800" />;
        case 'code':
            return (
                <pre
                    key={block.id}
                    className="bg-zinc-800 text-zinc-200 font-mono text-xs p-3 overflow-x-auto whitespace-pre-wrap break-words rounded-none"
                >
                    {block.text}
                </pre>
            );
        case 'quote':
            return (
                <blockquote
                    key={block.id}
                    className="border-l-4 border-accent pl-4 py-2 bg-zinc-900/60 text-zinc-300 italic text-sm"
                >
                    {parseInlineMarkdown(block.text)}
                </blockquote>
            );
        case 'table':
            return renderTable(block);
        case 'list':
            return renderList(block);
        default:
            return renderParagraph(block);
    }
}

/**
 * Custom zero-dependency block & inline Markdown renderer for React.
 */
export function MarkdownBlocks({ content }: { content: string }) {
    return <>{parseBlocks(content).map(renderBlock)}</>;
}
