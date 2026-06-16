import os, re
root = r'D:\pythonTtest\ai-test-management-system\frontend\src'
cnt = 0
for dp, _, fs in os.walk(root):
    for f in fs:
        if not f.endswith('.tsx'):
            continue
        for i, l in enumerate(open(os.path.join(dp, f), encoding='utf-8-sig')):
            if re.search(r'\b(?:text|bg|border|fill)-(?:gray|red|blue|emerald|amber|indigo|cyan|slate)-[456789]00\b', l) and 'dark:' not in l:
                cnt += 1
print(f'Remaining issues: {cnt}')
