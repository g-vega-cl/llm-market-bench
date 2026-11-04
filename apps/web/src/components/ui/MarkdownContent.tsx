import { MarkdownBlocks, type MarkdownContentProps } from './markdown-blocks';

export {
    InlineMarkdown,
    type InlineMarkdownProps,
    parseInlineMarkdown,
} from './markdown-inline';

/**
 * Custom zero-dependency block & inline Markdown Renderer for React.
 */
export function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
    if (!content?.trim()) return null;

    return (
        <div className={`flex flex-col gap-3 ${className}`}>
            <MarkdownBlocks content={content} />
        </div>
    );
}
