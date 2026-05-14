#!/usr/bin/env python3
"""Batch-fix useButtonType: add type="button" to buttons lacking type attribute."""
import re, sys

button_pattern = re.compile(
    r'(<\s*button\b)((?:(?!type\s*=)[^>])*?)>',
    re.IGNORECASE | re.DOTALL
)

def has_no_type(attrs):
    return 'type=' not in attrs.lower()

def add_button_type(m):
    prefix, attrs = m.group(1), m.group(2) or ''
    if has_no_type(attrs):
        return f'{prefix} type="button"{attrs}>'
    return m.group(0)

for filepath in sys.argv[1:]:
    with open(filepath, 'r') as f:
        content = f.read()
    new_content, n = button_pattern.subn(add_button_type, content)
    if n > 0:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"FIXED {n} in {filepath}")
    else:
        print(f"NONE in {filepath}")
