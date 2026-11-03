"""Turn verdict.json files into tracker status writes, and optionally an open-issues-only source page.

  python statuses.py OLD_DATA.json OUT_DIR "<date, e.g. 3 Nov 2026>" [WORK=work/_golive] [--open-src SAVED.html]

Writes OUT_DIR/ops.json (one {doc_id, data} per issue), OUT_DIR/db/<doc_id>.json (the document body,
for ArtifactData batch file_path entries), and with --open-src also OUT_DIR/open_src.html: the old page
with only the issues that are not fixed (langs narrowed to the still-failing locales), ready for upgrade.py.
Prints the counts, the non-fixed issues and the pages that are fully clean now.
"""
import datetime, json, os, re, sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
data, out, date = args[0], args[1], args[2]
work = args[3] if len(args) > 3 else 'work/_golive'
d = json.load(open(data, encoding='utf8'))
now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
os.makedirs(out + '/db', exist_ok=True)
ops, cnt, clean, verdicts = [], {}, [], {}
for p in d['pages']:
    if not p['issues']:
        clean.append(p['label'] + ' (no issues before)'); continue
    v = json.load(open(f"{work}/{p['slug']}/verdict.json", encoding='utf8'))
    assert sorted(x['id'] for x in v) == sorted(i['id'] for i in p['issues']), 'ids differ: ' + p['slug']
    verdicts[p['slug']] = {x['id']: x for x in v}
    if all(x['verdict'] == 'fixed' for x in v):
        clean.append(p['label'])
    for x in v:
        k = x['verdict']; cnt[k] = cnt.get(k, 0) + 1
        if k == 'fixed':
            st, fl = 'Fixed', f"Verified fixed on www (go-live re-check {date})"
        elif k == 'partly':
            st, fl = 'Open', f"Fixed in {', '.join(x['fixed_langs'])}; still on www in {', '.join(x['still_langs'])} ({date})"
        elif k == 'still':
            st, fl = 'Open', f"Still on www at go-live re-check {date}: {x['now']}"
        else:
            st, fl = 'Open', f"Not re-checked: {x['now']}"
        doc = f"{p['slug']}_{x['id']}"
        body = {"status": st, "flag": fl, "updatedAt": now, "by": None}
        ops.append({"doc_id": doc, "data": body})
        json.dump(body, open(f"{out}/db/{doc}.json", 'w', encoding='utf8'), ensure_ascii=False)
        if k != 'fixed':
            print(f"{doc}  {k}  | {fl}")
json.dump(ops, open(out + '/ops.json', 'w', encoding='utf8'), ensure_ascii=False)
print(cnt, len(ops), 'issues')
print('clean:', ', '.join(clean))

if '--open-src' in sys.argv:
    src = sys.argv[sys.argv.index('--open-src') + 1]
    h = open(src, encoding='utf8').read()
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', h, re.S)
    od = json.loads(m.group(1).replace('<\\/', '</'))
    pages = []
    for p in od['pages']:
        vv = {i: x for i, x in verdicts.get(p['slug'], {}).items() if x['verdict'] != 'fixed'}
        if not vv:
            continue
        p['issues'] = [i for i in p['issues'] if i['id'] in vv]
        for i in p['issues']:
            x = vv[i['id']]
            if x['still_langs']:
                i['langs'] = x['still_langs']
            i['issue'] += ' (open on www at go-live re-check: ' + x['now'] + ')'
        pages.append(p)
    keep = {p['slug'] for p in pages}
    for p in pages:
        for i in p['issues']:
            i['also'] = [s for s in i.get('also', []) if s in keep]
    ids = {(p['slug'], i['id']) for p in pages for i in p['issues']}
    od['pages'] = pages
    od['shared'] = [g for g in od.get('shared', []) if sum(tuple(r) in ids for r in g['refs']) > 1]
    for g in od['shared']:
        g['refs'] = [r for r in g['refs'] if tuple(r) in ids]
    blob = json.dumps(od, ensure_ascii=False).replace('</', '<\\/')
    open(out + '/open_src.html', 'w', encoding='utf8').write(h[:m.start(1)] + blob + h[m.end(1):])
    print('open-only source:', sum(len(p['issues']) for p in pages), 'issues on', len(pages), 'pages')
