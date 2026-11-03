"""Pull the QA-log data out of a saved artifact page.

  python extract.py SAVED.html OUT_DIR [WORK=work/_golive]

Writes OUT_DIR/old_data.json and WORK/<slug>/old_issues.json for every page.
"""
import json, os, re, sys

src, out = sys.argv[1], sys.argv[2]
work = sys.argv[3] if len(sys.argv) > 3 else 'work/_golive'
h = open(src, encoding='utf8').read()
m = re.search(r'<script type="application/json" id="data">(.*?)</script>', h, re.S)
if not m:
    sys.exit('No <script id="data"> block in ' + src)
d = json.loads(m.group(1).replace('<\\/', '</'))
os.makedirs(out, exist_ok=True)
json.dump(d, open(os.path.join(out, 'old_data.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
n = 0
for p in d['pages']:
    os.makedirs(f"{work}/{p['slug']}", exist_ok=True)
    keep = {k: p.get(k) for k in 'slug label uat live checked issues not_issues couldnt_check'.split()}
    json.dump(keep, open(f"{work}/{p['slug']}/old_issues.json", 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    n += len(p['issues'])
    print(f"{p['slug']}  {len(p['issues'])} issues  {p['live']}")
print(f"{len(d['pages'])} pages, {n} issues")
