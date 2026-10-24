"""Read an older QA-log artifact that has no JSON data (a pre-rendered page: <section class="page">
with <article class="issue"> rows and a <ul class="shared-list">) and return the same data
structure that upgrade.py works on. Needs beautifulsoup4."""
import re
from bs4 import BeautifulSoup
from common import LOC


def is_static(html):
    return 'class="shared-list"' in html and '<article class="issue"' in html


def scrape(html):
    soup = BeautifulSoup(html, 'html.parser')
    codes = [c for c, _ in LOC]
    intro = (soup.select_one('p.intro') or soup.new_tag('p')).get_text(' ', strip=True)
    date = re.search(r'checked ([0-9]+ [A-Za-z]+ [0-9]{4})', intro)
    pages, shared = [], []
    for sec in soup.select('section.page'):
        slug = sec['id'][2:] if sec.get('id', '').startswith('p-') else sec.get('id', '')
        label = sec.select_one('h2').get_text(strip=True)
        links = [a['href'] for a in sec.select('p.urls a')]
        issues = []
        for art in sec.select('article.issue'):
            badges = [b for b in art.select('header .badge') if 'shared' not in b.get('class', [])]
            vs = {dt['class'][0]: dt.find_next('dd').get_text(' ', strip=True) for dt in art.select('dl.vs dt')}
            cause = art.select_one('p.cause')
            btn = art.select_one('button.shots')
            shots = {k: btn['data-' + k] for k in ('uat', 'live') if btn and btn.get('data-' + k)}
            sh = art.select_one('a.badge.shared')
            issues.append(dict(
                id=int(art.select_one('.num').get_text(strip=True).lstrip('#')),
                component=(art.select_one('.comp') or soup.new_tag('x')).get_text(' ', strip=True),
                kind=badges[0].get_text(strip=True) if badges else 'Other',
                issue=art.select_one('p.what').get_text(' ', strip=True),
                uat=vs.get('uat', ''), live=vs.get('live', ''),
                cause=re.sub(r'^Likely cause\s*', '', cause.get_text(' ', strip=True)) if cause else '',
                langs=[s.get_text(strip=True) for s in art.select('.strip .loc.on')],
                shots=shots, group=sh['href'][1:] if sh else '', also=[]))
        pages.append(dict(slug=slug, label=label, title=label, uat=links[0] if links else '', live=links[1] if len(links) > 1 else '',
                          checked=codes, issues=issues, not_issues=[], couldnt_check=[], updated=date.group(1) if date else ''))
    by = {p['slug']: p for p in pages}
    for li in soup.select('.shared-list > li'):
        meta = li.select_one('p.meta')
        badge = meta.select_one('.badge')
        refs = []
        for a in li.select('p.hits a'):
            slug, _, num = a['href'][1:].rpartition('-')
            if slug in by and num.isdigit():
                refs.append([slug, int(num)])
        shared.append(dict(id=li['id'], title=li.select_one('p.what').get_text(' ', strip=True),
                           kind=badge.get_text(strip=True) if badge else 'Other', refs=refs))
    for g in shared:
        for s, i in g['refs']:
            x = next((x for x in by[s]['issues'] if x['id'] == i), None)
            if x: x['also'] = sorted({r[0] for r in g['refs'] if r[0] != s})
    h1 = soup.select_one('h1').get_text(strip=True)
    title = soup.title.get_text(strip=True) if soup.title else h1
    return dict(locales=LOC, title=title, heading=h1, intro=intro, heat_note='', built=date.group(1) if date else '',
                pages=pages, shared=shared)
