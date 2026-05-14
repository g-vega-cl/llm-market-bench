#!/usr/bin/env python3
"""Batch-fix noSvgWithoutTitle: add <title>SVG</title> on a NEW LINE after <svg...>"""
import re, sys

svg_block_pattern = re.compile(
    r'(<svg\b[^>]*>)((?:(?!</svg>).)*?)(</svg>)',
    re.IGNORECASE | re.DOTALL
)

total = 0
def add_title(m):
    global total
    svg_open, inner, svg_close = m.group(1), m.group(2), m.group(3)
    if '<title>' in inner.lower():
        return m.group(0)
    total += 1
    # Put title on its own line as the first child
    return f'{svg_open}\n<title>SVG</title>{inner}{svg_close}'

for filepath in sys.argv[1:]:
    before = total
    with open(filepath, 'r') as f:
        content = f.read()
    new_content, n = svg_block_pattern.subn(add_title, content)
    added = total - before
    if added > 0:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"FIXED {added} in {filepath}")
    else:
        print(f"NONE in {filepath}")
