"""Fix all dark mode issues across entire frontend src/ directory."""
import os, re

ROOT = r'D:\pythonTtest\ai-test-management-system\frontend\src'

RULES = [
    # text-gray variants
    (r'text-gray-900(?![/\w-])', 'dark:text-gray-100'),
    (r'text-gray-800(?![/\w-])', 'dark:text-gray-200'),
    (r'text-gray-700(?![/\w-])', 'dark:text-gray-300'),
    (r'text-gray-600(?![/\w-])', 'dark:text-gray-400'),
    (r'text-gray-500(?![/\w-])', 'dark:text-gray-400'),
    (r'text-gray-400(?![/\w-])', 'dark:text-gray-500'),
    (r'text-black(?![/\w-])', 'dark:text-white'),
    # bg variants
    (r'bg-white(?![/\w-])', 'dark:bg-gray-800'),
    (r'bg-gray-50(?![/\w-])', 'dark:bg-gray-800/50'),
    (r'bg-gray-100(?![/\w-])', 'dark:bg-gray-800'),
    (r'hover:bg-gray-50(?![/\w-])', 'dark:hover:bg-gray-800'),
    # border variants
    (r'border-gray-200(?![/\w-])', 'dark:border-gray-700'),
    (r'border-gray-300(?![/\w-])', 'dark:border-gray-600'),
    # fill
    (r'fill-gray-800(?![/\w-])', 'dark:fill-gray-200'),
    # slate
    (r'text-slate-600(?![/\w-])', 'dark:text-slate-300'),
    (r'text-slate-500(?![/\w-])', 'dark:text-slate-400'),
    (r'border-slate-200(?![/\w-])', 'dark:border-slate-800'),
    # red
    (r'text-red-700(?![/\w-])', 'dark:text-red-400'),
    (r'text-red-600(?![/\w-])', 'dark:text-red-400'),
    (r'text-red-500(?![/\w-])', 'dark:text-red-400'),
    (r'bg-red-50(?![/\w-])', 'dark:bg-red-900/20'),
    (r'bg-red-100(?![/\w-])', 'dark:bg-red-900/30'),
    (r'border-red-200(?![/\w-])', 'dark:border-red-800'),
    (r'text-red-800(?![/\w-])', 'dark:text-red-300'),
    # blue
    (r'text-blue-600(?![/\w-])', 'dark:text-blue-400'),
    (r'text-blue-500(?![/\w-])', 'dark:text-blue-400'),
    (r'text-blue-700(?![/\w-])', 'dark:text-blue-300'),
    (r'bg-blue-50(?![/\w-])', 'dark:bg-blue-900/20'),
    (r'bg-blue-100(?![/\w-])', 'dark:bg-blue-900/30'),
    (r'text-blue-800(?![/\w-])', 'dark:text-blue-300'),
    # emerald
    (r'text-emerald-700(?![/\w-])', 'dark:text-emerald-400'),
    (r'bg-emerald-50(?![/\w-])', 'dark:bg-emerald-900/20'),
    # amber
    (r'text-amber-700(?![/\w-])', 'dark:text-amber-400'),
    (r'text-amber-600(?![/\w-])', 'dark:text-amber-400'),
    (r'text-amber-800(?![/\w-])', 'dark:text-amber-300'),
    (r'bg-amber-50(?![/\w-])', 'dark:bg-amber-900/20'),
    (r'border-amber-200(?![/\w-])', 'dark:border-amber-800'),
    # indigo
    (r'text-indigo-700(?![/\w-])', 'dark:text-indigo-300'),
    (r'bg-indigo-50(?![/\w-])', 'dark:bg-indigo-900/20'),
    # cyan
    (r'text-cyan-700(?![/\w-])', 'dark:text-cyan-300'),
    (r'bg-cyan-50(?![/\w-])', 'dark:bg-cyan-900/20'),
]

fixed = 0
for dirpath, _, filenames in os.walk(ROOT):
    for f in filenames:
        if not f.endswith('.tsx'):
            continue
        filepath = os.path.join(dirpath, f)
        lines = open(filepath, encoding='utf-8-sig').readlines()
        changed = False

        for i, line in enumerate(lines):
            original = line
            # Find all className="..." or className={`...`} substrings
            parts = re.findall(
                r'className\s*=\s*["`]([^"`]*)["`]',
                line
            )
            for part in parts:
                modified = part
                for pattern, dark_variant in RULES:
                    if re.search(pattern, modified) and dark_variant not in modified:
                        # Check if same dark prefix already exists
                        dark_prefix = dark_variant.split(':')[1].split('-')[0]
                        if re.search(rf'dark:{dark_prefix}-', modified):
                            continue
                        modified = modified.rstrip() + ' ' + dark_variant

                if modified != part:
                    line = line.replace(part, modified, 1)

            if line != original:
                lines[i] = line
                changed = True

        if changed:
            open(filepath, 'w', encoding='utf-8-sig').writelines(lines)
            fixed += 1
            print(f'  FIXED: {filepath}')

print(f'\nTotal files fixed: {fixed}')
