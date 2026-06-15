"""
Batch-add dark: variants to hardcoded Tailwind color classes in TSX files.

Problem: Many pages use text-gray-900, bg-gray-50, bg-white etc. without
corresponding dark: counterparts, making text unreadable in dark mode.

This script safely adds the dark variant to any className string that has
a light-mode color class but lacks its dark-mode equivalent.
"""
import os
import re

ROOT = r'D:\pythonTtest\ai-test-management-system\frontend\src\pages'

# Mapping: light class regex pattern -> dark variant to append (when missing)
# Key format: (regex_to_find, dark_variant_to_add)
# We check that the dark variant is NOT already in the same className to avoid doubles.
RULES = [
    # Text colors: light-on-dark needs light text
    (r'text-gray-900(?![/\w-])', 'dark:text-gray-100'),
    (r'text-gray-800(?![/\w-])', 'dark:text-gray-200'),
    (r'text-gray-700(?![/\w-])', 'dark:text-gray-300'),
    (r'text-gray-600(?![/\w-])', 'dark:text-gray-400'),
    (r'text-gray-500(?![/\w-])', 'dark:text-gray-400'),
    (r'text-black(?![/\w-])', 'dark:text-white'),

    # Background colors: light bg on dark needs dark bg
    (r'bg-white(?![/\w-])', 'dark:bg-gray-800'),
    (r'bg-gray-50(?![/\w-])', 'dark:bg-gray-800/50'),
    (r'bg-gray-100(?![/\w-])', 'dark:bg-gray-800'),

    # Hover backgrounds
    (r'hover:bg-gray-50(?![/\w-])', 'dark:hover:bg-gray-800'),

    # Borders
    (r'border-gray-200(?![/\w-])', 'dark:border-gray-700'),
    (r'border-gray-300(?![/\w-])', 'dark:border-gray-600'),

    # SVG fill
    (r'fill-gray-800(?![/\w-])', 'dark:fill-gray-200'),

    # text-slate (used in layout)
    (r'text-slate-600(?![/\w-])', 'dark:text-slate-300'),
    (r'text-slate-500(?![/\w-])', 'dark:text-slate-400'),

    # border-slate
    (r'border-slate-200(?![/\w-])', 'dark:border-slate-800'),
]

# Specific files to skip (already properly handled or not relevant)
SKIP_FILES = set()


def extract_classname_strings(line: str):
    """
    Find all className="..." or className={`...`} substrings in a line.
    Returns list of (start, end, content) tuples.
    """
    results = []
    # Match className="..." (simple string)
    for m in re.finditer(r'className\s*=\s*"([^"]*)"', line):
        results.append((m.start(), m.end(), m.group(1), '"'))
    # Match className={`...`} (template literal)  
    for m in re.finditer(r'className\s*=\s*\{`([^`]*)`\}', line):
        results.append((m.start(), m.end(), m.group(1), '`'))
    return results


def process_file(filepath: str):
    """Process a single TSX file, adding dark variants where needed."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    original = content
    lines = content.split('\n')
    changed = False

    for i, line in enumerate(lines):
        classname_blocks = extract_classname_strings(line)
        if not classname_blocks:
            continue

        new_line = line
        for start, end, class_str, quote_char in classname_blocks:
            modified = class_str

            for light_pattern, dark_variant in RULES:
                # Check if light class exists
                if not re.search(light_pattern, modified):
                    continue

                # Check if dark variant already exists in this className string
                if dark_variant in modified:
                    continue

                # Also check if there's already ANY dark: variant for the same property
                # e.g., if 'dark:text-' already exists, skip adding another text color
                dark_prefix = dark_variant.split(':')[1].split('-')[0]  # e.g., 'text' from 'dark:text-gray-100'
                if dark_prefix in ('bg', 'text', 'border', 'fill', 'hover'):
                    # Check if same type dark variant exists
                    if re.search(rf'dark:{dark_prefix}-', modified):
                        continue

                # Add the dark variant at the end of the className string
                modified = modified.rstrip() + ' ' + dark_variant
                changed = True

            if modified != class_str:
                # Reconstruct the className attribute with the same quote style
                if quote_char == '"':
                    new_attr = f'className="{modified}"'
                else:
                    new_attr = f'className={{`{modified}`}}'
                new_line = new_line[:start] + new_attr + new_line[end:]
                # Adjust positions for remaining blocks in the same line

        if new_line != line:
            lines[i] = new_line

    if changed:
        new_content = '\n'.join(lines)
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            f.write(new_content)
        return True
    return False


def main():
    fixed_count = 0
    file_count = 0

    for dirpath, dirnames, filenames in os.walk(ROOT):
        for filename in filenames:
            if not filename.endswith('.tsx'):
                continue
            filepath = os.path.join(dirpath, filename)
            if filename in SKIP_FILES:
                continue
            if process_file(filepath):
                fixed_count += 1
                print(f'  FIXED: {filepath}')
            file_count += 1

    print(f'\nProcessed {file_count} files, fixed {fixed_count} files.')


if __name__ == '__main__':
    main()
