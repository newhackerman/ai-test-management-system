import os, re
root = r'D:\pythonTtest\ai-test-management-system\frontend\src'
pages = {}
for dp, _, fs in os.walk(root):
    for f in fs:
        if not f.endswith(('.tsx', '.ts')):
            continue
        fp = os.path.join(dp, f)
        short = fp.replace(root, '').replace('\\', '/')
        for i, l in enumerate(open(fp, encoding='utf-8-sig')):
            if re.search(r'\b(?:text|bg|border|fill)-(?:gray|red|blue|emerald|amber|indigo|cyan|slate|orange|purple)-[456789]00\b', l) and 'dark:' not in l:
                pages.setdefault(short, []).append((i+1, l.rstrip()[:120]))

for f, issues in sorted(pages.items()):
    print(f'\n{f} ({len(issues)} issues):')
    for n, l in issues[:3]:
        print(f'  L{n}: {l}')

print(f'\nTotal files with issues: {len(pages)}')
print(f'Total issues: {sum(len(v) for v in pages.values())}')
