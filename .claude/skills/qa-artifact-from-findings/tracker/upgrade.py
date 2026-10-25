"""Upgrade an existing QA-log artifact page to the tracker format.

  python upgrade.py SOURCE.html OUT.html [--title "Page name"] [--heading "..."]

SOURCE is the saved HTML of a QA-log artifact (the Artifact tool's read saves it). Its data
(<script type="application/json" id="data">, or `const DATA = {...}`) is kept as it is; each issue
gains severity, UI flag, issue types (Source 404, Content Missing, Missing Image, UI, ...) and the
Messy flag is worked out per page. Shared groups gain an id, a likely fix and types. The page
itself is written from src/head.html and src/app.js next to this file, so every upgraded artifact looks
and behaves like the special-pages tracker. Screenshots keep their paths, so a republish to the
same artifact keeps them. Prints what changed so the counts can be checked before publishing.
"""
import json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

SRC = pathlib.Path(__file__).resolve().parent / 'src'


def load_data(html):
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S)
    if m:
        return json.loads(m.group(1).replace('<\\/', '</'))
    m = re.search(r'const DATA\s*=\s*(\{.*?\});\s*\n', html, re.S)
    if m:
        return json.loads(m.group(1))
    import static_import
    if static_import.is_static(html):
        return static_import.scrape(html)
    sys.exit('No QA-log data found in the source page.')


def upgrade(d, sections=None):
    for p in d['pages']:
        for i in p['issues']:
            i.setdefault('shots', {}); i.setdefault('also', []); i.setdefault('langs', []); i.setdefault('cause', '')
            i.setdefault('uat', ''); i.setdefault('live', ''); i.setdefault('component', ''); i.setdefault('group', '')
            i['sig'] = i.get('signature') or i.get('group') or ''
            raw = dict(i, kind=i['kind'], signature=i['sig'])
            i['kind'] = norm_kind(raw)
            i['sev'] = severity(i['kind'], i['sig'])
            i['ui'] = is_ui(i['kind'], i['sig'])
            i['quick'] = 'Unpublish in Sitecore' if i['kind'] == 'Source 404' or i['sig'] == 'faq-extra-locales' else ''
            i['rc'] = ''
            i['types'] = types_of(i['kind'], i['ui'], i['issue'] + ' | ' + i['uat'], i['component'], i['sig'], i['live'])
        p['messy'] = messy_check(p['issues'], (sections or {}).get(p['slug'], 0), bool(p.get('version_mismatch')))
        p.setdefault('not_issues', []); p.setdefault('couldnt_check', [])
    by = {p['slug']: p for p in d['pages']}
    used = set()
    for g in d.get('shared', []):
        base = re.sub(r'[^a-z0-9]+', '-', g['title'].lower()).strip('-')[:40] or 'group'
        gid, n = base, 2
        while gid in used:
            gid = f'{base}-{n}'; n += 1
        used.add(gid); g['id'] = gid
        members = [x for s, i in g['refs'] for x in by[s]['issues'] if x['id'] == i] if all(s in by for s, _ in g['refs']) else []
        g['types'] = [t for t in TYPE_ORDER if any(t in x['types'] for x in members)] or ['Other']
        g['fix'], g['note'] = FIX_BY_TYPE[g['types'][0]]
        if 'kind' not in g: g['kind'] = g['types'][0]
    d['type_order'] = TYPE_ORDER
    return d


def page_html(d, html_title=None):
    """The tracker page: head + the data as JSON + the app script."""
    title = html_title or d.get('title') or 'QA log'
    head = (SRC / 'head.html').read_text(encoding='utf8')
    head = re.sub(r'<title>.*?</title>', lambda m: '<title>' + title + '</title>', head, count=1, flags=re.S)
    app = (SRC / 'app.js').read_text(encoding='utf8')
    blob = json.dumps(d, ensure_ascii=False).replace('</', '<'+chr(92)+'/').replace(chr(0xfffd), chr(92) + 'ufffd')
    nl = chr(10)
    return head + nl + '<script type="application/json" id="data">' + blob + '</script>' + nl + '<script>' + nl + app + '</script>' + nl


def summary(d):
    n = sum(len(p['issues']) for p in d['pages'])
    types = {}
    for p in d['pages']:
        for i in p['issues']:
            for t in i['types']: types[t] = types.get(t, 0) + 1
    sev = {}
    for p in d['pages']:
        for i in p['issues']: sev[i['sev']] = sev.get(i['sev'], 0) + 1
    return n, types, sev, [p['label'] for p in d['pages'] if p['messy']['on']]


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    html = pathlib.Path(sys.argv[1]).read_text(encoding='utf8')
    d = load_data(html)
    before = [(p['slug'], i['id'], tuple(sorted(i.get('shots', {}).items()))) for p in d['pages'] for i in p['issues']]
    d = upgrade(d)
    after = [(p['slug'], i['id'], tuple(sorted(i['shots'].items()))) for p in d['pages'] for i in p['issues']]
    if before != after:
        sys.exit('Issue ids or screenshots changed during the upgrade; not written.')
    if '--heading' in sys.argv:
        d['heading'] = sys.argv[sys.argv.index('--heading') + 1]
    if '--title' in sys.argv:
        d['title'] = sys.argv[sys.argv.index('--title') + 1]
    title = d.get('title') or re.search(r'<title>(.*?)</title>', html, re.S).group(1)
    pathlib.Path(sys.argv[2]).write_text(page_html(d, title), encoding='utf8')
    n, types, sev, messy = summary(d)
    print(f'{n} issues kept, {len(d["pages"])} pages, {len(d.get("shared", []))} shared groups')
    print('types', types); print('severity', sev); print('messy', messy)
