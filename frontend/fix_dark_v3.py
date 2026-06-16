import os, re

ROOT = r'D:\pythonTtest\ai-test-management-system\frontend\src'

# Skip patterns that are deliberately light-on-dark or button/badge colors
SKIP_INVERTED = re.compile(
    r'\b(?:bg-(?:blue|red|emerald|amber|indigo|cyan|purple|orange|green|yellow|pink)-[56]00|bg-gray-[89]00|bg-slate-[89]00)\b'
    r'|\btext-white\b'
    r'|\banimate-spin\b'  # spinner borders
    r'|\bborder-b-2\b'     # spinner borders
    r'|\bhover:bg-\w+-[67]00\b'  # hover on dark bg
    r'|\bscale-\d+\b'     # scale utilities
    r'|\btouch-\w+\b'     # touch utilities
    r'|\bsafe-area-\w+\b' # safe area utilities
)

# Light class -> dark variant mappings
RULES = [
    ('text-gray-900', 'dark:text-gray-100'),
    ('text-gray-800', 'dark:text-gray-200'),
    ('text-gray-700', 'dark:text-gray-300'),
    ('text-gray-600', 'dark:text-gray-400'),
    ('text-gray-500', 'dark:text-gray-400'),
    ('bg-white', 'dark:bg-gray-800'),
    ('bg-gray-50', 'dark:bg-gray-800/50'),
    ('bg-gray-100', 'dark:bg-gray-800'),
    ('bg-gray-200', 'dark:bg-gray-600'),
    ('bg-gray-300', 'dark:bg-gray-500'),
    ('bg-gray-400', 'dark:bg-gray-500'),
    ('border-gray-200', 'dark:border-gray-700'),
    ('border-gray-300', 'dark:border-gray-600'),
    ('text-red-700', 'dark:text-red-400'),
    ('text-red-800', 'dark:text-red-300'),
    ('text-red-600', 'dark:text-red-400'),
    ('text-red-500', 'dark:text-red-400'),
    ('bg-red-50', 'dark:bg-red-900/20'),
    ('bg-red-100', 'dark:bg-red-900/30'),
    ('border-red-200', 'dark:border-red-800'),
    ('text-blue-900', 'dark:text-blue-100'),
    ('text-blue-700', 'dark:text-blue-300'),
    ('text-blue-800', 'dark:text-blue-300'),
    ('text-blue-600', 'dark:text-blue-400'),
    ('text-blue-500', 'dark:text-blue-400'),
    ('bg-blue-50', 'dark:bg-blue-900/20'),
    ('bg-blue-100', 'dark:bg-blue-900/30'),
    ('border-blue-200', 'dark:border-blue-800'),
    ('text-emerald-600', 'dark:text-emerald-400'),
    ('text-emerald-700', 'dark:text-emerald-400'),
    ('bg-emerald-50', 'dark:bg-emerald-900/20'),
    ('text-amber-900', 'dark:text-amber-100'),
    ('text-amber-800', 'dark:text-amber-300'),
    ('text-amber-700', 'dark:text-amber-400'),
    ('text-amber-600', 'dark:text-amber-400'),
    ('text-amber-500', 'dark:text-amber-400'),
    ('bg-amber-50', 'dark:bg-amber-900/20'),
    ('bg-amber-100', 'dark:bg-amber-900/30'),
    ('border-amber-200', 'dark:border-amber-800'),
    ('text-orange-800', 'dark:text-orange-300'),
    ('text-orange-700', 'dark:text-orange-400'),
    ('text-orange-600', 'dark:text-orange-400'),
    ('text-orange-500', 'dark:text-orange-400'),
    ('bg-orange-50', 'dark:bg-orange-900/20'),
    ('bg-orange-100', 'dark:bg-orange-900/30'),
    ('text-purple-800', 'dark:text-purple-300'),
    ('text-purple-700', 'dark:text-purple-400'),
    ('text-purple-600', 'dark:text-purple-400'),
    ('text-purple-500', 'dark:text-purple-400'),
    ('bg-purple-50', 'dark:bg-purple-900/20'),
    ('bg-purple-100', 'dark:bg-purple-900/30'),
    ('text-indigo-800', 'dark:text-indigo-300'),
    ('text-indigo-700', 'dark:text-indigo-300'),
    ('text-indigo-600', 'dark:text-indigo-400'),
    ('bg-indigo-50', 'dark:bg-indigo-900/20'),
    ('bg-indigo-100', 'dark:bg-indigo-900/30'),
    ('text-cyan-700', 'dark:text-cyan-300'),
    ('text-cyan-600', 'dark:text-cyan-400'),
    ('bg-cyan-50', 'dark:bg-cyan-900/20'),
    ('text-slate-700', 'dark:text-slate-300'),
    ('text-slate-600', 'dark:text-slate-300'),
    ('bg-slate-100', 'dark:bg-slate-800'),
    ('text-green-600', 'dark:text-green-400'),
    ('text-green-500', 'dark:text-green-400'),
    ('bg-green-500', 'dark:bg-green-600'),
    ('fill-gray-600', 'dark:fill-gray-300'),
    ('fill-gray-700', 'dark:fill-gray-200'),
]

SKIP_FILES = {'fix_dark_mode_colors.py', 'fix_all_dark.py', 'fix_dashboard_dark.py',
              'fix_dark_v2.py', 'fix_dark_v3.py', 'check_dark.py', 'check_remaining.py'}

fixed = 0

for dirpath, _, filenames in os.walk(ROOT):
    for fname in filenames:
        if not fname.endswith(('.tsx', '.ts')):
            continue
        if fname in SKIP_FILES:
            continue

        filepath = os.path.join(dirpath, fname)
        try:
            lines = open(filepath, encoding='utf-8-sig').readlines()
        except Exception:
            continue

        changed = False

        for i, line in enumerate(lines):
            orig = line

            # Skip if already has dark: variants
            if 'dark:' in line:
                continue

            # Skip if this line has an inverted pattern (deliberate light-on-dark)
            if SKIP_INVERTED.search(line):
                continue

            # Find ALL quoted strings (single quotes, double quotes, backticks)
            # that look like CSS class strings
            parts = re.findall(r"['\"`]([^'\"`]{4,})['\"`]", line)
            for part in parts:
                # Only process strings that contain Tailwind-like classes
                if not re.search(r'\b(?:text|bg|border|fill)-\w+-\d+\b', part):
                    continue
                if 'dark:' in part:
                    continue
                if SKIP_INVERTED.search(part):
                    continue

                modified = part
                any_change = False

                for light_class, dark_variant in RULES:
                    if light_class in modified:
                        dark_prefix = dark_variant.split(':')[1].split('-')[0]
                        if re.search(rf'dark:{dark_prefix}-', modified):
                            continue
                        modified = modified.rstrip() + ' ' + dark_variant
                        any_change = True

                if any_change and modified != part:
                    line = line.replace(part, modified, 1)

            if line != orig:
                lines[i] = line
                changed = True

        if changed:
            open(filepath, 'w', encoding='utf-8-sig').writelines(lines)
            fixed += 1
            print(f'  FIXED: {filepath}')

print(f'\nTotal files fixed: {fixed}')
