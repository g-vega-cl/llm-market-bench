import type React from 'react';

export interface InlineMarkdownProps {
    text?: string | null;
    className?: string;
}

const SAFE_URL = /^(https?:|mailto:|\/|#)/i;

/** Only http(s), mailto and relative/anchor URLs are clickable. */
export function isSafeUrl(url: string): boolean {
    return SAFE_URL.test(url.trim());
}

function renderLink(fullMatch: string, key: string): React.ReactNode {
    const linkMatch = fullMatch.match(/^\[(.*?)\]\((.*?)\)$/);
    const linkText = linkMatch?.[1] || '';
    const url = linkMatch?.[2] || '';
    if (!isSafeUrl(url)) {
        return <span key={key}>{linkText}</span>;
    }
    return (
        <a
            key={key}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent hover:underline font-bold text-xs"
        >
            {linkText}
        </a>
    );
}

function renderTokenNode(fullMatch: string, key: string): React.ReactNode {
    if (fullMatch.startsWith('***') || fullMatch.startsWith('___')) {
        const inner = fullMatch.slice(3, -3);
        return (
            <strong key={key} className="font-bold text-white">
                <em className="italic text-zinc-300">{parseInlineMarkdown(inner)}</em>
            </strong>
        );
    }
    if (fullMatch.startsWith('**') || fullMatch.startsWith('__')) {
        const inner = fullMatch.slice(2, -2);
        return (
            <strong key={key} className="font-bold text-white">
                {parseInlineMarkdown(inner)}
            </strong>
        );
    }
    if (fullMatch.startsWith('*') || fullMatch.startsWith('_')) {
        const inner = fullMatch.slice(1, -1);
        return (
            <em key={key} className="italic text-zinc-300">
                {parseInlineMarkdown(inner)}
            </em>
        );
    }
    if (fullMatch.startsWith('`')) {
        const inner = fullMatch.slice(1, -1);
        return (
            <code
                key={key}
                className="px-1.5 py-0.5 rounded-none bg-zinc-800 text-accent font-mono text-xs font-bold"
            >
                {inner}
            </code>
        );
    }
    if (fullMatch.startsWith('[')) {
        return renderLink(fullMatch, key);
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
