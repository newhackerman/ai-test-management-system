import os, re

ROOT = r'D:\pythonTtest\ai-test-management-system\frontend\src'

# Rules: (light_pattern, dark_replacement_for_static, dark_suffix_for_class_str)
RULES = [
    ('text-gray-900', 'dark:text-gray-100'),
    ('text-gray-800', 'dark:text-gray-200'),
    ('text-gray-700', 'dark:text-gray-300'),
    ('text-gray-600', 'dark:text-gray-400'),
    ('text-gray-500', 'dark:text-gray-400'),
    ('bg-white', 'dark:bg-gray-800'),
    ('bg-gray-50', 'dark:bg-gray-800/50'),
    ('bg-gray-100', 'dark:bg-gray-800'),
    ('border-gray-200', 'dark:border-gray-700'),
    ('border-gray-300', 'dark:border-gray-600'),
    ('text-red-700', 'dark:text-red-400'),
    ('text-red-800', 'dark:text-red-300'),
    ('text-red-600', 'dark:text-red-400'),
    ('bg-red-50', 'dark:bg-red-900/20'),
    ('bg-red-100', 'dark:bg-red-900/30'),
    ('border-red-200', 'dark:border-red-800'),
    ('text-red-900', 'dark:text-red-300'),
    ('text-blue-700', 'dark:text-blue-300'),
    ('text-blue-800', 'dark:text-blue-300'),
    ('bg-blue-50', 'dark:bg-blue-900/20'),
    ('bg-blue-100', 'dark:bg-blue-900/30'),
    ('text-amber-700', 'dark:text-amber-400'),
    ('text-amber-800', 'dark:text-amber-300'),
    ('bg-amber-50', 'dark:bg-amber-900/20'),
    ('text-orange-700', 'dark:text-orange-400'),
    ('bg-orange-50', 'dark:bg-orange-900/20'),
    ('text-emerald-700', 'dark:text-emerald-400'),
    ('text-purple-700', 'dark:text-purple-400'),
    ('bg-purple-50', 'dark:bg-purple-900/20'),
    ('text-indigo-700', 'dark:text-indigo-300'),
    ('text-cyan-700', 'dark:text-cyan-300'),
]

# Patterns that are deliberately light-on-dark and should NOT be touched
SKIP_INVERTED = [
    r'bg-blue-600\b', r'bg-red-600\b', r'bg-emerald-600\b', r'bg-amber-600\b',
    r'bg-indigo-600\b', r'bg-cyan-600\b', r'bg-purple-600\b', r'bg-orange-600\b',
    r'bg-gray-800\b', r'bg-gray-900\b', r'bg-slate-800\b', r'bg-slate-900\b',
    r'bg-red-500\b', r'bg-blue-500\b',
    r'text-white\b',
]

SKIP_FILES = {
    'fix_dark_mode_colors.py', 'fix_all_dark.py', 'fix_dashboard_dark.py', 'check_dark.py',
    'fix_dark_v2.py',
}

fixed = 0

for dirpath, _, filenames in os.walk(ROOT):
    for fname in filenames:
        if not fname.endswith('.tsx') and not fname.endswith('.ts'):
            continue
        if fname in SKIP_FILES:
            continue

        filepath = os.path.join(dirpath, fname)
        try:
            content = open(filepath, encoding='utf-8-sig').read()
        except Exception:
            continue

        changed = False
        lines = content.split('\n')

        for i, line in enumerate(lines):
            orig = line

            # Strategy: find ALL class name strings in the line (className="...", className={`...`}, and JS string constants)
            # Then for each found class string, check each rule and append dark variant if:
            # - The light class exists
            # - The dark variant does NOT already exist
            # - The class string does NOT contain an inverted bg pattern

            # Find all quoted strings that contain Tailwind-like classes
            # This catches: className="..." / className={`...`} / 'bg-red-100 text-red-800' / etc.
            parts = re.findall(r'["`\']([^"`\']{3,})["`\']', line)
            for part in parts:
                # Skip if this isn't a CSS class string
                if not re.search(r'\b(?:text|bg|border|fill|hover:bg)-\w+-\d+\b', part):
                    continue

                # Skip if already has dark: variant
                if 'dark:' in part:
                    continue

                # Skip if contains deliberately inverted patterns (light text on dark bg)
                has_inverted = any(re.search(p, part) for p in SKIP_INVERTED)
                if has_inverted:
                    continue

                modified = part
                any_modified = False

                for light_class, dark_variant in RULES:
                    if light_class in modified:
                        # Check if same property dark variant exists
                        dark_prefix = dark_variant.split(':')[1].split('-')[0]
                        if re.search(rf'dark:{dark_prefix}-', modified):
                            continue
                        modified = modified.rstrip() + ' ' + dark_variant
                        any_modified = True

                if any_modified and modified != part:
                    line = line.replace(part, modified, 1)

            if line != orig:
                lines[i] = line
                changed = True

        if changed:
            open(filepath, 'w', encoding='utf-8-sig').write('\n'.join(lines))
            fixed += 1
            print(f'  FIXED: {filepath}')

print(f'\nTotal files fixed: {fixed}')
