"""Re-check bookkeeping for the special-pages QA tracker.

  python artifact-special/recheck.py snapshot SLUG [SLUG ...]   before re-running a page
  python artifact-special/recheck.py merge    SLUG [SLUG ...]   after the new findings.json is written

snapshot keeps the previous findings and screenshots. merge compares new findings with the
previous ones by signature, so an issue keeps its id (and its shared status, assignee and notes)
across runs. It writes the merged findings.json (plus resolved_issues) and work/_recheck_plan.json,
which lists what to change in the artifact's shared database and in the published files.
Run from the project folder.
"""
import json, pathlib, re, shutil, sys, datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import GROUPS, LABEL

W = pathlib.Path('.')
canon = lambda sig: GROUPS.get(sig, sig)
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
ident = lambda i: canon(i.get('signature')) or (i['component'], i['kind'])


def check(slugs):
    bad = [s for s in slugs if s not in LABEL]
    if bad or not slugs:
        sys.exit(f"Unknown or missing page slug(s) {bad}. Known: {', '.join(LABEL)}")


def snapshot(slugs):
    for s in slugs:
        f = W / 'work' / s / 'findings.json'
        shutil.copy(f, f.with_name('findings.prev.json'))
        shots, prev = W / 'reports' / 'screenshots' / s, W / 'reports' / 'screenshots' / (s + '.prev')
        if prev.exists():
            shutil.rmtree(prev)
        if shots.exists():
            shutil.copytree(shots, prev)
        print('snapshot', s, len(load(f)['issues']), 'issues')


def merge(slugs):
    today = datetime.date.today()
    date_txt = today.strftime('%d %B %Y').lstrip('0')
    plan = {'date': date_txt, 'pages': {}, 'files': {}, 'remove': [], 'db': []}
    for s in slugs:
        d = W / 'work' / s
        prev, new = load(d / 'findings.prev.json'), load(d / 'findings.json')
        if new.get('round') == prev.get('round', 1) + 1 and 'resolved_issues' in new:
            sys.exit(f'{s}: findings.json is already merged. Run snapshot and re-analyse first.')
        rnd = prev.get('round', 1) + 1
        pool = [dict(i, _was_resolved=False) for i in prev['issues']] + [dict(i, _was_resolved=True) for i in prev.get('resolved_issues', [])]
        top = max([i['id'] for i in pool] + [0])
        shots_dir, prev_dir = W / 'reports' / 'screenshots' / s, W / 'reports' / 'screenshots' / (s + '.prev')
        keep, out_issues, tags = {}, [], {'still': [], 'new': [], 'regressed': []}
        for n in new['issues']:
            cand = [p for p in pool if ident(p) == ident(n)]
            m = next((p for p in cand if p['component'] == n['component']), cand[0] if cand else None)
            if m:
                pool.remove(m); fid = m['id']; tag = 'regressed' if m['_was_resolved'] else 'still'
            else:
                top += 1; fid = top; tag = 'new'
            tags[tag].append(fid)
            shots = {}
            for side, rel in (n.get('shots') or {}).items():
                src = W / 'reports' / rel
                if not src.exists():
                    continue
                rest = re.sub(r'^\d+-', '', src.stem)
                name = f'screenshots/{s}/{fid}-{rest}-r{rnd}{src.suffix}'
                keep[name] = src.read_bytes(); shots[side] = name
            out_issues.append(dict(n, id=fid, shots=shots, recheck=tag))
        resolved, newly = [], []
        for p in pool:
            if not p['_was_resolved']:
                newly.append(p['id'])
            r = {k: v for k, v in p.items() if k not in ('_was_resolved',)}
            r.setdefault('resolved_on', date_txt)
            for side, rel in (r.get('shots') or {}).items():
                for base in (prev_dir, shots_dir):
                    f = base / pathlib.Path(rel).name
                    if f.exists():
                        keep.setdefault(rel, f.read_bytes()); break
            resolved.append(r)
        old_files = {f'screenshots/{s}/{f.name}' for f in shots_dir.glob('*')} if shots_dir.exists() else set()
        if shots_dir.exists():
            shutil.rmtree(shots_dir)
        shots_dir.mkdir(parents=True)
        for rel, b in keep.items():
            (W / 'reports' / rel).write_bytes(b)
        plan['remove'] += sorted(old_files - set(keep))
        plan['files'].update({rel: 'reports/' + rel for rel in keep})
        new_doc = dict(new, issues=out_issues, resolved_issues=resolved, round=rnd, rechecked_on=date_txt)
        (d / 'findings.json').write_text(json.dumps(new_doc, ensure_ascii=False, indent=1), encoding='utf8')
        fixed = newly
        key = lambda i: f'{s}_{i}'
        summ = f"{len(tags['new'])} new, {len(tags['still'])} still failing, {len(fixed)} gone, {len(tags['regressed'])} came back"
        plan['pages'][s] = {'fixed': [key(i) for i in fixed], 'still': [key(i) for i in tags['still']],
                            'new': [key(i) for i in tags['new']], 'regressed': [key(i) for i in tags['regressed']], 'summary': summ}
        print(f'{s}: {summ}')
    (W / 'work' / '_recheck_plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf8')
    print('wrote work/_recheck_plan.json')


if __name__ == '__main__':
    cmd, slugs = (sys.argv[1] if len(sys.argv) > 1 else ''), sys.argv[2:]
    if cmd not in ('snapshot', 'merge'):
        sys.exit(__doc__)
    check(slugs)
    (snapshot if cmd == 'snapshot' else merge)(slugs)
