import re

P = r'D:\pythonTtest\ai-test-management-system\frontend\src\pages\Dashboard.tsx'
with open(P, 'r', encoding='utf-8-sig') as f:
    c = f.read()

# Fix CompactMetric emphasis colors
c = c.replace(
    "emphasis ? 'text-red-700' : 'text-gray-900'",
    "emphasis ? 'text-red-700 dark:text-red-400' : 'text-gray-900 dark:text-gray-100'"
)

# Fix error banner
c = c.replace(
    '"rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"',
    '"rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-400"'
)

# Fix no-access banner
c = c.replace(
    '"rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"',
    '"rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 px-4 py-3 text-sm text-amber-800 dark:text-amber-400"'
)

# Fix metric tone values (JS string attributes)
tones = [
    ("'bg-blue-50 text-blue-700'", "'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'"),
    ("'bg-red-50 text-red-700'", "'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300'"),
    ("'bg-emerald-50 text-emerald-700'", "'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'"),
    ("'bg-amber-50 text-amber-700'", "'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'"),
    ("'bg-indigo-50 text-indigo-700'", "'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300'"),
    ("'bg-cyan-50 text-cyan-700'", "'bg-cyan-50 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300'"),
]
for old, new in tones:
    c = c.replace(old, new)

# Fix StatusBadge text-emerald
c = c.replace(
    "className={isDone ? 'text-emerald-700' : undefined}",
    "className={isDone ? 'text-emerald-700 dark:text-emerald-300' : undefined}"
)

# Fix data source badge colors
c = c.replace(
    "className={source.available ? 'text-emerald-700' : 'text-gray-500'}",
    "className={source.available ? 'text-emerald-700 dark:text-emerald-300' : 'text-gray-500 dark:text-gray-400'}"
)

with open(P, 'w', encoding='utf-8-sig') as f:
    f.write(c)

print('Dashboard dark mode fixes applied.')
