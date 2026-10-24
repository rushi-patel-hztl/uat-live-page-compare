"""Build a UAT-vs-live QA tracker artifact (heat grid, shared faults, per-page issues, screenshots, status/owner tracking)
from the work/<slug>/findings.json files that the uat-live-page-compare skill writes.

Run from the project folder (the one that holds work/ and reports/):
  py -3.13 <skill>/build.py --out artifact-NAME --title "Solutions pages QA log" \
      --heading "TeamViewer solutions pages: internal vs live" --prefix solutions [--exclude solutions]
  or  --slugs a,b,c   or  --slugs-file work/pairs.txt  (paths or URLs, one per line; slug = path minus locale)

Writes OUT/index.html, OUT/packs/<slug>.txt (screenshots, base64 packs) and OUT/publish_batches.json
(lists of pack paths, each batch under ~55 MB, for successive Artifact publishes).
"""
import argparse, base64, collections, io, json, pathlib, re, struct, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / 'tracker'))
import upgrade as tracker
from urllib.parse import urlparse
from PIL import Image

HERE = pathlib.Path(__file__).parent
LOC = [["EN","English"],["DE","German"],["FR","French"],["ES","Spanish"],["JA","Japanese"],["PT","Portuguese"],["CN","Chinese (Simplified)"],["HU","Hungarian"],["IT","Italian"],["KO","Korean"],["NL","Dutch"],["PL","Polish"],["TH","Thai"],["RU","Russian"],["CS","Czech"],["TW","Chinese (Traditional)"],["TR","Turkish"]]
N2C = {n: c for c, n in LOC}

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--title", required=True, help="2-4 word page name, also the browser tab title")
ap.add_argument("--heading", default="")
ap.add_argument("--prefix", default="", help="use every slug in work/_progress.json that starts with this")
ap.add_argument("--slugs", default="")
ap.add_argument("--slugs-file", default="")
ap.add_argument("--exclude", default="", help="comma-separated slugs to leave out")
ap.add_argument("--date", default="")
ap.add_argument("--max-width", type=int, default=1280)
ap.add_argument("--quality", type=int, default=72)
a = ap.parse_args()
W = pathlib.Path(".")
OUT = pathlib.Path(a.out)
(OUT / "packs").mkdir(parents=True, exist_ok=True)


def slug_of(line):
    tok = line.split()[-1]
    path = urlparse(tok).path if "://" in tok else tok
    return "-".join(x for x in re.sub(r"^/[a-z]{2}(-[a-z]+)?/", "/", path).strip("/").split("/") if x)


if a.slugs:
    slugs = [s for s in a.slugs.split(",") if s]
elif a.slugs_file:
    slugs = [slug_of(l) for l in open(a.slugs_file, encoding="utf-8") if l.strip() and not l.startswith("#")]
else:
    reg = json.load(open(W / "work/_progress.json", encoding="utf-8-sig"))
    slugs = [s for s in reg["order"] if s.startswith(a.prefix)]
skip = set(x for x in a.exclude.split(",") if x)
slugs = [s for s in slugs if s not in skip and (W / "work" / s / "findings.json").exists()]
if not slugs:
    sys.exit("No pages with work/<slug>/findings.json found.")
date = a.date or __import__("datetime").date.today().strftime("%d %B %Y")


def label(s):
    if a.prefix and s.startswith(a.prefix + "-"):
        s = s[len(a.prefix) + 1:]
    return s.replace("-", " ").capitalize()


def sections_of(slug):
    n = 0
    for side in ("live", "uat"):
        try:
            n = max(n, len(re.findall("^#[0-9]+", (W / "work" / slug / f"en-{side}.txt").read_text(encoding="utf8"), re.M)))
        except OSError:
            pass
    return n


pages, sigs = [], collections.defaultdict(list)
for slug in slugs:
    f = json.load(open(W / "work" / slug / "findings.json", encoding="utf-8-sig"))
    plan = json.load(open(W / "work" / slug / "plan.json", encoding="utf-8-sig"))
    issues = []
    for i in f["issues"]:
        kind = i["kind"]
        if kind == "Locale" and i["live"].strip().startswith("404"):
            kind = "Source 404"
        elif kind == "Locale" and i["uat"].strip().startswith("404"):
            kind = "Target 404"
        sg = i.get("signature") or ""
        if sg:
            sigs[sg].append((slug, i["id"], i["issue"], kind))
        shots = {k: v for k, v in (i.get("shots") or {}).items() if (W / "reports" / v).exists()}
        issues.append(dict(id=i["id"], component=i["component"], kind=kind, issue=i["issue"], uat=i["uat"], live=i["live"],
                           cause=i.get("cause", ""), langs=[N2C[n] for n in i["languages"] if n in N2C], shots=shots,
                           group="", also=[], signature=sg))
    pages.append(dict(slug=slug, label=label(slug), title=f.get("title", slug), uat=plan["uat"], live=plan["live"],
                      checked=[c for c, _ in LOC if c in plan["locales"]], issues=issues,
                      not_issues=f.get("not_issues", []), couldnt_check=f.get("couldnt_check", []), updated=date,
                      version_mismatch=bool(f.get("version_mismatch"))))
by = {p["slug"]: p for p in pages}
shared = []
for sg, refs in sigs.items():
    if len({r[0] for r in refs}) < 2:
        continue
    shared.append(dict(title=collections.Counter(r[2] for r in refs).most_common(1)[0][0],
                       kind=collections.Counter(r[3] for r in refs).most_common(1)[0][0],
                       refs=[[r[0], r[1]] for r in refs]))
    for s, i, _, _ in refs:
        iss = [x for x in by[s]["issues"] if x["id"] == i][0]
        iss["also"] = sorted({r[0] for r in refs if r[0] != s})
        iss["group"] = sg
shared.sort(key=lambda g: -len({r[0] for r in g["refs"]}))

hits = collections.Counter(c for p in pages for i in p["issues"] for c in i["langs"])
worst = ", ".join(c for c, _ in hits.most_common(5))
n = sum(len(p["issues"]) for p in pages)
data = dict(
    locales=LOC, title=a.title, heading=a.heading or a.title,
    intro=(f"{len(pages)} pages compared between the internal (UAT) site and the live site in all 17 locales at 1440px wide, "
           f"header CTA and menu included, footer and top-bar utility links excluded; built {date}. Source 404 means live "
           f"(source) returns 404; Target 404 means the internal page (target) returns 404."),
    heat_note=f"{n} issues across {len(pages)} pages. Locales with the most issues: {worst}." if n else "",
    built=date, pages=pages, shared=shared)
data["packs"] = True
data = tracker.upgrade(data, {p["slug"]: sections_of(p["slug"]) for p in pages})
(OUT / "index.html").write_text(tracker.page_html(data, a.title), encoding="utf8")
n_, types_, sev_, messy_ = tracker.summary(data)
print("issue types", types_, "| severity", sev_, "| messy pages", len(messy_))

# One base64 pack per page: 4-byte header length + JSON {path:[offset,length]} + JPEG bytes.
# The artifact host caps one artifact at 512 files, and 1000+ screenshots would not fit as separate files.
sizes = {}
for pg in pages:
    idx, blobs, off = {}, [], 0
    for iss in pg["issues"]:
        for v in iss["shots"].values():
            if v in idx:
                continue
            im = Image.open(W / "reports" / v).convert("RGB")
            if im.width > a.max_width:
                im = im.resize((a.max_width, round(im.height * a.max_width / im.width)), Image.LANCZOS)
            b = io.BytesIO()
            im.save(b, "JPEG", quality=a.quality, optimize=True)
            d = b.getvalue()
            idx[v] = [off, len(d)]
            blobs.append(d)
            off += len(d)
    hdr = json.dumps(idx).encode()
    txt = base64.b64encode(struct.pack(">I", len(hdr)) + hdr + b"".join(blobs)).decode()
    (OUT / "packs" / f"{pg['slug']}.txt").write_text(txt)
    sizes[f"packs/{pg['slug']}.txt"] = len(txt)
batches, cur, cs = [], [], 0
for k, v in sizes.items():
    if cur and cs + v > 55e6:
        batches.append(cur)
        cur, cs = [], 0
    cur.append(k)
    cs += v
if cur:
    batches.append(cur)
(OUT / "publish_batches.json").write_text(json.dumps(batches, indent=1))
print(f"{len(pages)} pages, {n} issues, {len(shared)} shared groups, {sum(sizes.values())/1e6:.0f} MB of packs "
      f"in {len(batches)} publish batches -> {OUT}/")
