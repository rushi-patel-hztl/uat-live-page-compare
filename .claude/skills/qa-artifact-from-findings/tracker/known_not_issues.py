"""Differences we already know are NOT issues (the "Never report" rules in
uat-live-page-compare/SKILL.md, as patterns), so they never reach findings.json, a re-check or the tracker.

  python known_not_issues.py work/<slug>/findings.json [...]   moves matching issues to not_issues (in place)

Used by build.py (filters before building), recheck.py (old issues that are now known not-issues are dropped,
not counted as fixed) and by workers before writing findings.json. When a "Never report" rule is added to
SKILL.md, add its pattern here too. Keep patterns narrow: a missed match only costs a manual drop, a wrong
match hides a real bug.
"""
import json, pathlib, re, sys

HEX = lambda s: set(re.findall(r'#[0-9a-f]{6}', s))


def _txt(i):
    return ' | '.join(str(i.get(k, '')) for k in ('component', 'kind', 'issue', 'uat', 'live', 'signature')).lower()


def _rules(i):
    t, issue = _txt(i), str(i.get('issue', '')).lower()
    uat, live = str(i.get('uat', '')).lower(), str(i.get('live', '')).lower()
    sig, kind, comp = str(i.get('signature', '')), str(i.get('kind', '')).lower(), str(i.get('component', '')).lower()
    hu, hl = HEX(uat), HEX(live)
    broken = re.search(r"missing|doesn.t open|does not open|not open|no options|empty|\bno\b[^|]*dropdown|has no", issue)
    # 'Number of Employees' form dropdown ranges
    if 'number of employees' in t and re.search(r'range|option|1 - 4|1 - 5', t) and not broken and not re.search(
            r'placeholder|please select|business role|\bor\b|other field', issue):
        yield "'Number of Employees' dropdown ranges differ: expected difference."
    # decorative arrow beside / above a contact form, when the issue is only about the arrow
    if re.search(r'(decorative|hand-drawn|hand drawn|curved)[^|]{0,40}arrow', issue) and not re.search(
            r'padding|field|label|badge|gr[ae]y|taller|button|band|strip|colou?r|card|shadow|width|wide|styled|spans', issue):
        yield 'Decorative arrow beside the contact form missing on UAT: expected difference.'
    # hand-drawn arrow above the form, with card padding / field width / label position that follow from the form variant
    if re.search(r'arrow[^|]{0,50}form|form[^|]{0,80}arrow', issue) and not re.search(
            r'card arrow|arrow icon|asset|dropdown|placeholder|please select', issue) and re.search(r'\bform\b', t):
        yield 'Form variant (arrow above the form, card padding, field width, label position): expected per design.'
    if re.search(r'labels? (sit|are|above)[^|]{0,40}(above|inside)|labels above', issue) and re.search(r'\binputs?\b|\bfields?\b', issue) and 'form' in t:
        yield 'Form field label position (above vs floating inside): expected per design.'
    # hero sits lower under the header / Q&A top padding (section padding tokens)
    if re.search(r'space above the hero|hero spacing differs|hero content (sits|starts)|hero starts|hero has more space above', issue) and not re.search(
            r'column|wider|wrap|image (is )?smaller|colou?r|cta style', issue):
        yield 'Hero / section top spacing from padding tokens: expected per design.'
    # no divider above the first list / checklist row (list text colour is covered by the body-text rule)
    if not re.search(r'accordion|faq', t) and re.search(r'divider above the first|no divider above|top divider', issue) and not re.search(
            r'icon|image|radius|border colou?r|background', issue):
        yield 'Missing divider above the first list row: expected per design.'
    # tab / accordion URL query or hash: only presence is tested
    nohash = re.compile(r"does not|doesn.t|no (url )?hash|sets no|\bnone\b|no query|not set|missing|without")
    if re.search(r'different (url )?(hash|query)|different \?tab|(hash|query)[^|]{0,30}(values? )?differ|sets a [^|]{0,30}hash instead of', issue) \
            and not nohash.search(issue) and not nohash.search(uat) and not nohash.search(live):
        yield 'Tab / accordion URL query or hash set on both sides with different values: expected (only a missing one is reported).'
    # font size / weight
    if kind == 'font size' or re.search(r'^[^|]*font[- ](size|weight)s? (differ|is|are)', issue):
        yield 'Font size / weight difference: never reported.'
    if kind != 'accessibility' and 'link' not in issue:
        # body text #2D2D2D vs #545454 / #050A52
        if hu == {'#2d2d2d'} and hl and hl <= {'#545454', '#050a52'} and re.search(r'body|paragraph|text colou?r|copy', issue) \
                and not re.search(r'title|heading', issue):
            yield 'Body text #2D2D2D (UAT) vs #545454 / #050A52 (live): expected.'
        # navy titles vs near-black
        if hu == {'#050a52'} and hl and hl <= {'#141414', '#000000'} and re.search(r'title|heading|accordion|faq', issue):
            yield 'Title / heading text navy #050A52 (UAT) vs #141414 / #000000 (live): expected title colour.'
        # tab label colours
        if re.search(r'tab (label|title|text|name)s?', issue) and not re.search(r'divider|underline|border|background', issue) and hu and hu <= {'#3056ef', '#27272a', '#474747'} \
                and hl and hl <= {'#050a52', '#545454'}:
            yield 'Tab label colours (UAT #3056EF / #27272A vs live #050A52 / #545454): expected per design.'
    # divider above the first accordion row (accordion / FAQ only, and only that)
    if re.search(r'accordion|faq', t) and re.search(r'divider|line|border', issue) and re.search(
            r'above the first|first (row|item)', issue) and not re.search(r' and |padding|colou?r|icon', issue):
        yield 'Missing divider above the first accordion row: expected per design.'
    # <html lang> code variants of one language
    if re.search(r'html lang|lang attribute', issue) and 'zh' in t and not re.search(r'wrong language|english', issue):
        yield '<html lang> code variant of the same language: not reported.'
    # card / column / CTA width on its own
    if re.search(r'\b(card|column|cta|button)s? (is |are )?(width|wider|narrower)', issue) and not re.search(
            r'image|logo|border|gap|padding|height|taller|shorter|wrap|font|colou?r|icon|line|illustration|quote|indent|shift|crop', issue):
        yield 'Card / column / CTA width difference on its own: not reported.'
    # spacing of 2px or less
    m = re.match(r'gap:\d+:(\d+)>(\d+)$', sig)
    if m and abs(int(m.group(1)) - int(m.group(2))) <= 2:
        yield 'Spacing difference of 2px or less: ignored.'
    # header CTA design (UAT transparent / 8px radius vs live white / blue border / 4px radius)
    if comp.startswith('header') and 'cta' in t and re.search(r'radius|border', issue) and (
            '8px' in uat or 'transparent' in uat or '#3056ef' in live) and not re.search(
            r'missing|instead|404|text|label|destination|links? to|goes to|new tab|only|shows|localis|banner', issue):
        yield 'Header CTA design (border, radius, fill) differs by design: not reported.'


def known_not_issue(i):
    """Reason string when the issue is a known not-issue, else None."""
    return next(_rules(i), None)


def clean(doc):
    """Move known not-issues out of doc['issues'] (and resolved_issues) into doc['not_issues']. Returns dropped list."""
    dropped = []
    for key in ('issues', 'resolved_issues'):
        keep = []
        for i in doc.get(key, []):
            r = known_not_issue(i)
            if r:
                dropped.append((i.get('id'), i.get('signature', ''), r))
                ni = doc.setdefault('not_issues', [])
                if r not in ni:
                    ni.append(r)
            else:
                keep.append(i)
        if key in doc:
            doc[key] = keep
    return dropped


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        f = pathlib.Path(p)
        d = json.loads(f.read_text(encoding='utf-8-sig'))
        dropped = clean(d)
        if dropped:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf8')
        for i, s, r in dropped:
            print(f'{p}: dropped #{i} {s}: {r}')
        print(f'{p}: {len(dropped)} known not-issue(s) removed, {len(d.get("issues", []))} issues left')
