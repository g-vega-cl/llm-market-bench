---
tags: [frontend, markdown, rendering, security, ui]
category: concept
---

# Zero-Dependency Markdown Renderer

The web app renders LLM-authored Markdown (audience desk answers, memory cards, chat responses) without pulling in a Markdown library. The renderer is a small, hand-written, dependency-free pipeline split across four files under `apps/web/src/components/ui/`. It parses a string into a typed block tree and renders it to React nodes, supporting bold/italic/code/links inline, headings, horizontal rules, blockquotes, tables, fenced code blocks, and nested lists.

## Module Layout

The renderer was decomposed into vertical slices so each concern (parsing, inline tokens, block rendering, public wrapper) lives in its own file:

- **`markdown-parse.ts`** — the line-based block parser. Exports the `Block` union (`heading`, `hr`, `code`, `quote`, `table`, `para`, `list`), the `ListBlock`/`ListItemNode`/`Cell` types, and `parseBlocks(content)`. Every node carries a stable `id` minted from a monotonic cursor (`b0`, `b1`, …) so React never needs array-index keys.
- **`markdown-inline.tsx`** — inline token parsing. Exports `parseInlineMarkdown(text)`, `InlineMarkdown`, `InlineMarkdownProps`, and the URL-safety guard `isSafeUrl(url)`.
- **`markdown-blocks.tsx`** — the React renderers. Exports `MarkdownBlocks` (maps the parsed block tree to elements) and the `MarkdownContentProps` interface.
- **`MarkdownContent.tsx`** — the thin public wrapper. Re-exports `InlineMarkdown`, `InlineMarkdownProps`, and `parseInlineMarkdown` from `markdown-inline`, and renders `<MarkdownBlocks content={content} />` inside a `flex flex-col gap-3` container. Returns `null` for empty/whitespace-only content.

## Block Parser (`markdown-parse.ts`)

`parseBlocks` normalizes CRLF to LF, splits into lines, and walks a cursor, dispatching each non-blank line to a block parser:

- **Fenced code** (` ``` `) — consumes lines verbatim until the closing fence; content is preserved exactly (no inline parsing inside).
- **Horizontal rule** — matches `-`, `*`, or `_` repeated 3+ times (with optional spaces).
- **Heading** — `#{1,4}` with optional trailing `#`s; level clamped to 1–4.
- **Blockquote** — consecutive `>` lines, stripped of the marker.
- **Table** — detected when a line contains `|` and the next line is a separator row (`:?-{2,}:?` cells). Rows are split on `|` with leading/trailing pipes trimmed. Detection does **not** require a blank line before the table, so a table can follow a paragraph line directly.
- **List** — unordered (`-`, `*`, `•`) or ordered (`1.`, `1)`, or `**1.**`). Items are collected flat with their indent width, then `buildList` recursively nests deeper-indented items as `children` of the preceding item. Continuation lines (indented, non-block-start) are appended to the previous item's text.
- **Paragraph** — everything else; consecutive non-block-start lines are collected as `lines`.

`isBlockStart` is the shared predicate that decides whether a line terminates the current paragraph/list, checking for blank lines, fences, rules, headings, quotes, list items, and table starts.

## Inline Parsing (`markdown-inline.tsx`)

`parseInlineMarkdown` runs a single regex over the text, matching `***bold italic***`, `___bold italic___`, `**bold**`, `__bold__`, `*italic*`, `_italic_` (word-boundary guarded), `` `code` ``, and `[link](url)`. Each match is rendered by `renderTokenNode`; unmatched spans pass through as plain text.

### URL Safety

`isSafeUrl(url)` only permits `http:`, `https:`, `mailto:`, and relative/anchor URLs (`/`, `#`). A link whose target fails the check (e.g. `javascript:alert(1)`) is rendered as a plain `<span>` of the link text rather than an anchor, preventing script-injection via LLM-authored Markdown. Safe links render as `<a target="_blank" rel="noopener noreferrer">`.

## Rendering (`markdown-blocks.tsx`)

`renderBlock` switches on `block.kind`:

- **heading** — `h1`–`h4` with display-font styling; `h2` carries a bottom border.
- **hr** — a `border-t` divider.
- **code** — a `<pre>` with `whitespace-pre-wrap break-words` so long lines wrap instead of overflowing.
- **quote** — a left-bordered blockquote with inline parsing.
- **table** — a horizontally scrollable `<table>` with bold header cells and inline-parsed body cells.
- **list** — `<ul>`/`<ol>` with `list-inside`, recursively rendering `item.children` as nested lists.
- **para** — a `<p>` where each source line is separated by a `<br />` (soft line breaks preserved), each line inline-parsed.

Because every node carries a stable `id`, repeated list items (e.g. three identical `- same` lines) render without React duplicate-key warnings.

## Consumers

The renderer is the shared Markdown surface for LLM prose. `apps/web/src/features/home/components/ConsoleQueueCard.tsx` renders the audience desk explainer's `agent_response` through `MarkdownContent` (see [[entities/live-agent-trader]] and [[entities/conversational-explainer]]), so bold emphasis, `---` rules, headings, and tables in the model's answer display as formatted prose rather than raw Markdown.

The audience **question** itself is rendered through the inline-only `InlineMarkdown` export inside a labeled `Question` block (`data-testid="answered-question"`). That block preserves line breaks with `whitespace-pre-wrap`, wraps long tokens with `break-words`, and applies a muted accent left rule, so multi-line or emphasized questions (e.g. `**inflation**` on one line, a follow-up on the next) are formatted inline instead of dumped as raw text. Because it uses `InlineMarkdown` rather than the full `MarkdownContent`, block-level constructs (headings, tables, rules) are not interpreted inside a question — only inline emphasis, code, and links.

## Testing

`apps/web/src/components/ui/MarkdownContent.test.tsx` covers horizontal rules, soft line breaks, lists directly after paragraph lines, tables following a paragraph without a blank line, fenced code rendered verbatim, nested lists, unsafe-link stripping, and duplicate-key suppression for repeated list items. `ConsoleQueueCard.test.tsx` verifies the desk answer renders as formatted Markdown (bold, `hr`, `h3`, table) with no raw `**` or `|---|` leaking through, and that the audience question renders inline Markdown (bold `**inflation**` becomes a `<strong>`, no raw `**`) inside the `answered-question` block carrying `whitespace-pre-wrap` and `break-words`.

## Related

- [[entities/live-agent-trader]] — the console card that renders desk answers and audience questions through this renderer
- [[entities/conversational-explainer]] — the LLM that produces the Markdown prose
- [[entities/web-app]] — the dashboard that hosts the shared UI components
- [[concepts/vertical-slice-islands]] — the decomposition pattern the renderer follows
