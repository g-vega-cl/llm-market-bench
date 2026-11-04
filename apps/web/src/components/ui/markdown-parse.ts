/**
 * Line-based block parser for the zero-dependency Markdown renderer.
 * Produces a typed block tree with stable ids (no index keys needed at render time).
 */

export interface Cell {
    id: string;
    text: string;
}

export interface ListItemNode {
    id: string;
    text: string;
    children: ListBlock[];
}

export interface ListBlock {
    id: string;
    kind: 'list';
    ordered: boolean;
    items: ListItemNode[];
}

export type Block =
    | { id: string; kind: 'heading'; level: number; text: string }
    | { id: string; kind: 'hr' }
    | { id: string; kind: 'code'; text: string }
    | { id: string; kind: 'quote'; text: string }
    | { id: string; kind: 'table'; headers: Cell[]; rows: { id: string; cells: Cell[] }[] }
    | { id: string; kind: 'para'; lines: string[] }
    | ListBlock;

interface FlatItem {
    indent: number;
    ordered: boolean;
    text: string;
}

const HR = /^\s*([-*_])(\s*\1){2,}\s*$/;
const HEADING = /^\s{0,3}(#{1,4})\s+(.+?)\s*#*\s*$/;
const FENCE = /^\s*```/;
const UL = /^(\s*)[-*•]\s+(.*)$/;
const OL = /^(\s*)(?:\d+[.)]|\*\*\d+[.)]\*\*)\s+(.*)$/;
const TABLE_SEP = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

function matchItem(line: string): FlatItem | null {
    const ul = line.match(UL);
    if (ul && !HR.test(line)) {
        return { indent: ul[1].replace(/\t/g, '    ').length, ordered: false, text: ul[2] };
    }
    const ol = line.match(OL);
    if (ol) {
        return { indent: ol[1].replace(/\t/g, '    ').length, ordered: true, text: ol[2] };
    }
    return null;
}

function isTableStart(lines: string[], i: number): boolean {
    return (
        lines[i].includes('|') &&
        i + 1 < lines.length &&
        lines[i + 1].includes('|') &&
        TABLE_SEP.test(lines[i + 1])
    );
}

function splitRow(row: string): string[] {
    let r = row.trim();
    if (r.startsWith('|')) r = r.slice(1);
    if (r.endsWith('|')) r = r.slice(0, -1);
    return r.split('|').map((c) => c.trim());
}

function isBlockStart(lines: string[], i: number): boolean {
    const line = lines[i];
    return (
        !line.trim() ||
        FENCE.test(line) ||
        HR.test(line) ||
        HEADING.test(line) ||
        /^\s*>/.test(line) ||
        matchItem(line) !== null ||
        isTableStart(lines, i)
    );
}

interface Cursor {
    lines: string[];
    i: number;
    seq: number;
}

const nextId = (c: Cursor) => `b${c.seq++}`;

function buildList(c: Cursor, items: FlatItem[], pos: { n: number }, base: number): ListBlock {
    const ordered = items[pos.n].ordered;
    const list: ListBlock = { id: nextId(c), kind: 'list', ordered, items: [] };
    while (pos.n < items.length) {
        const it = items[pos.n];
        if (it.indent < base) break;
        if (it.indent > base) {
            const parent = list.items[list.items.length - 1];
            if (!parent) break;
            parent.children.push(buildList(c, items, pos, it.indent));
            continue;
        }
        if (it.ordered !== ordered) break;
        list.items.push({ id: nextId(c), text: it.text, children: [] });
        pos.n++;
    }
    return list;
}

function parseCode(c: Cursor): Block {
    const code: string[] = [];
    c.i++;
    while (c.i < c.lines.length && !FENCE.test(c.lines[c.i])) code.push(c.lines[c.i++]);
    c.i++;
    return { id: nextId(c), kind: 'code', text: code.join('\n') };
}

function parseQuote(c: Cursor): Block {
    const quote: string[] = [];
    while (c.i < c.lines.length && /^\s*>/.test(c.lines[c.i])) {
        quote.push(c.lines[c.i++].replace(/^\s*>\s?/, ''));
    }
    return { id: nextId(c), kind: 'quote', text: quote.join('\n') };
}

function parseTable(c: Cursor): Block {
    const toCells = (row: string): Cell[] => splitRow(row).map((text) => ({ id: nextId(c), text }));
    const headers = toCells(c.lines[c.i]);
    c.i += 2;
    const rows: { id: string; cells: Cell[] }[] = [];
    while (c.i < c.lines.length && c.lines[c.i].trim() && c.lines[c.i].includes('|')) {
        rows.push({ id: nextId(c), cells: toCells(c.lines[c.i++]) });
    }
    return { id: nextId(c), kind: 'table', headers, rows };
}

function parseLists(c: Cursor): Block[] {
    const flat: FlatItem[] = [];
    while (c.i < c.lines.length) {
        const item = matchItem(c.lines[c.i]);
        if (item) {
            flat.push(item);
        } else if (/^\s+\S/.test(c.lines[c.i]) && !isBlockStart(c.lines, c.i)) {
            flat[flat.length - 1].text += ` ${c.lines[c.i].trim()}`;
        } else break;
        c.i++;
    }
    const out: Block[] = [];
    const pos = { n: 0 };
    while (pos.n < flat.length) {
        const before = pos.n;
        out.push(buildList(c, flat, pos, Math.min(flat[0].indent, flat[pos.n].indent)));
        if (pos.n === before) pos.n++;
    }
    return out;
}

function parseParagraph(c: Cursor): Block {
    const para: string[] = [];
    while (c.i < c.lines.length && (para.length === 0 || !isBlockStart(c.lines, c.i))) {
        para.push(c.lines[c.i++].trim());
    }
    return { id: nextId(c), kind: 'para', lines: para };
}

function parseNext(c: Cursor): Block[] {
    const line = c.lines[c.i];
    if (FENCE.test(line)) return [parseCode(c)];
    if (HR.test(line)) {
        c.i++;
        return [{ id: nextId(c), kind: 'hr' }];
    }
    const heading = line.match(HEADING);
    if (heading) {
        c.i++;
        return [{ id: nextId(c), kind: 'heading', level: heading[1].length, text: heading[2] }];
    }
    if (/^\s*>/.test(line)) return [parseQuote(c)];
    if (isTableStart(c.lines, c.i)) return [parseTable(c)];
    if (matchItem(line)) return parseLists(c);
    return [parseParagraph(c)];
}

export function parseBlocks(content: string): Block[] {
    const c: Cursor = { lines: content.replace(/\r\n?/g, '\n').split('\n'), i: 0, seq: 0 };
    const blocks: Block[] = [];
    while (c.i < c.lines.length) {
        if (c.lines[c.i].trim()) blocks.push(...parseNext(c));
        else c.i++;
    }
    return blocks;
}
