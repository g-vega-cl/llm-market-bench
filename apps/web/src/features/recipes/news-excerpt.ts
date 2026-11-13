const EXCERPT_RADIUS = 150;
const EXCERPT_LEAD_CHARS = 300;

/** Bounded body excerpt centered on the first keyword hit (else the lead). Mirrors engine `build_news_excerpt`. */
export function buildNewsExcerpt(fullText: string | null | undefined, keywords: string[]): string {
    const text = (fullText || '').replace(/[ \t\r\n\f\v\u00a0]+/g, ' ').replace(/^ | $/g, '');
    if (!text) return '';
    let lower = text.toLowerCase();
    if (lower.length !== text.length) lower = text; // keep indices aligned
    const hits = keywords
        .map((k) => k.trim().toLowerCase())
        .filter(Boolean)
        .map((k) => lower.indexOf(k))
        .filter((i) => i >= 0);
    if (hits.length === 0) {
        return text.length <= EXCERPT_LEAD_CHARS
            ? text
            : `${text.slice(0, EXCERPT_LEAD_CHARS).trimEnd()}…`;
    }
    const pos = Math.min(...hits);
    let start = Math.max(0, pos - EXCERPT_RADIUS);
    let end = Math.min(text.length, pos + EXCERPT_RADIUS);
    if (start > 0) {
        const sp = text.indexOf(' ', start);
        if (sp !== -1 && sp < pos) start = sp + 1;
    }
    if (end < text.length) {
        const sp = text.lastIndexOf(' ', end - 1);
        if (sp >= pos) end = sp;
    }
    return `${start > 0 ? '…' : ''}${text.slice(start, end)}${end < text.length ? '…' : ''}`;
}
