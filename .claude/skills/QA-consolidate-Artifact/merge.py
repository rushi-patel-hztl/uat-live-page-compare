#!/usr/bin/env python3
"""Merge several QA-log artifact pages into one.

Usage: python -I merge.py OUT_DIR TEMPLATE FILE=URL [FILE=URL ...]
FILE is the local html saved by the Artifact read action, URL its claude.ai artifact link.
Writes OUT_DIR/index.html and OUT_DIR/batches/batch_N.json (server-side copy maps, <=250 files each).
"""
import re, json, sys, os, difflib

out, tpl, *pairs = sys.argv[1:]
srcs = [p.rsplit('=', 1) for p in pairs]


def load(f):
    t = open(f, encoding='utf8').read()
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', t, re.S)
    if not m:
        m = re.search(r'const DATA = (\{.*?\});\n', t, re.S)
    return json.loads(m.group(1))


def norm_page(p, locales, date):
    """Bring any known page shape (old: name/codes/languages; current: label/checked/langs) to the current one."""
    code = {n: c for c, n in locales}
    q = dict(slug=p['slug'], label=p.get('label') or p.get('name'), title=p.get('title') or p.get('name'),
             uat=p['uat'], live=p['live'], checked=p.get('checked') or p.get('codes'), issues=[],
             not_issues=p.get('not_issues', []), couldnt_check=p.get('couldnt_check', []),
             updated=p.get('updated') or date or '')
    for i in p['issues']:
        langs = i.get('langs') or [code.get(l, l) for l in i.get('languages', [])]
        q['issues'].append(dict(id=i['id'], component=i['component'], kind=i['kind'], issue=i['issue'], uat=i['uat'],
                                live=i['live'], cause=i.get('cause', ''), langs=langs, shots=i.get('shots', {}),
                                group=i.get('group', ''), also=i.get('also', [])))
    return q


pages, shared_all, locales, dates, srcmap = [], [], None, [], {}
for f, url in srcs:
    d = load(f)
    locales = locales or d['locales']
    date = d.get('built') or d.get('date')
    dates.append(date)
    for p in d['pages']:
        pages.append(norm_page(p, d['locales'], date))
        for i in p['issues']:
            for s in i.get('shots', {}).values():
                if s:
                    srcmap[s] = url          # screenshot path -> artifact that holds it
    for g in d.get('shared', []):
        shared_all.append(dict(title=g['title'], kind=g.get('kind'), refs=g['refs']))

by = {}
for p in pages:
    by[p['slug']] = p                        # duplicate slug: later source wins
pages = sorted(by.values(), key=lambda p: p['slug'])   # URL-path order keeps parents before children
by = {p['slug']: p for p in pages}

labels = {}
for p in pages:
    labels.setdefault(p['label'], []).append(p)
for lab, ps in labels.items():
    if len(ps) > 1:                          # make duplicate labels unique; rename meaningfully afterwards
        for p in ps:
            p['label'] = f"{lab} ({p['slug'].replace('platform-one-', '').replace('-', ' ')})"

for g in shared_all:
    g['refs'] = [r for r in g['refs'] if r[0] in by]
    if g['kind'] is None and g['refs']:
        s, i = g['refs'][0]
        g['kind'] = next(x['kind'] for x in by[s]['issues'] if x['id'] == i)

# auto-merge groups with the same kind and similar title - REVIEW the printed MERGED lines
merged = []
for g in shared_all:
    for m in merged:
        if m['kind'] == g['kind'] and difflib.SequenceMatcher(None, m['title'].lower(), g['title'].lower()).ratio() >= .6:
            m['refs'] = [list(x) for x in dict.fromkeys(tuple(x) for x in m['refs'] + g['refs'])]
            print('MERGED:', m['title'], '<=', g['title'])
            break
    else:
        merged.append(dict(g, refs=[list(x) for x in g['refs']]))
order = [p['slug'] for p in pages]
for g in merged:
    g['refs'].sort(key=lambda r: (order.index(r[0]), r[1]))
merged = [g for g in merged if g['refs']]

total = sum(len(p['issues']) for p in pages)
D = dict(locales=locales, title='TeamViewer ONE QA log', heading='TeamViewer ONE pages: internal vs live',
         intro=f"All {len(pages)} pages compared between UAT and live in 17 locales; consolidated from {len(srcs)} QA logs.",
         heat_note='', built=max(x for x in dates if x), pages=pages, shared=merged)

t = open(tpl, encoding='utf8').read()
m = re.search(r'<script type="application/json" id="data">(.*?)</script>', t, re.S)
js = json.dumps(D, ensure_ascii=False).replace('</', '<\\/')
os.makedirs(out + '/batches', exist_ok=True)
open(out + '/index.html', 'w', encoding='utf8').write(t[:m.start(1)] + js + t[m.end(1):])

used = sorted({s for p in pages for i in p['issues'] for s in i['shots'].values() if s})
for n, k in enumerate(range(0, len(used), 250), 1):
    json.dump({s: {"artifact": srcmap[s], "path": s} for s in used[k:k + 250]},
              open(f'{out}/batches/batch_{n}.json', 'w'), separators=(',', ':'))
print(f'{len(pages)} pages, {total} issues, {len(merged)} shared groups, {len(used)} screenshots, '
      f'{-(-len(used) // 250)} batches')
for g in merged:
    print(' S', g['kind'], '|', g['title'], len(g['refs']))
