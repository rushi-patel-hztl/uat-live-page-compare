"""Batch pipeline for many pages: plan locales, capture everything in parallel,
pre-compare, and track progress.

Usage (run from the project folder):
  python batch.py plan <pairs.txt> [--locales EN,DE] [--concurrency 10]
        pairs.txt: one page per line, "<UAT URL> <live URL>" (space, tab or comma
        separated; lines starting with # are skipped). Finds every locale URL
        from the live page's hreflang links and registers each page as pending.
  python batch.py capture [--slugs a,b] [--concurrency 10] [--shots en|all|none] [--shard i/n]
        Captures UAT + live for every locale of every pending page (one Chrome,
        N tabs), then runs diff.py on each page as soon as its last locale is
        in. Pages become "captured" in the order given. Safe to run in the
        background while pages are being analysed. --shots: full-page slices
        for EN only (default; other locales are confirmed with capture_issues.py),
        every locale, or none. --shard 1/3, 2/3, 3/3: split the pending pages
        over several capture processes running at the same time.
  python batch.py progress              progress bar and counts
  python batch.py next <n>              claim the next n captured pages (-> analysing), print slugs
  python batch.py mark <slug> <done|failed|captured|pending> [--issues N] [--note "..."] [--confluence <page URL>] [--keep]
        done also deletes the page's capture images (unless --keep).
  python batch.py list [status]         slugs with their status

Files: work/_progress.json (registry), work/<slug>/plan.json, snapshots,
slices, diff.md, findings.json.
"""
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from playwright.async_api import async_playwright

import diff
from browse import capture
from pw import open_browser, pool

WORK = Path.cwd() / "work"
REG = WORK / "_progress.json"
LOCK = WORK / "_progress.lock"
WIDTH = 1440  # wide enough that the full main navigation (and its top-right CTA) shows
DEFAULT_SEG = {"EN": "en", "DE": "de", "FR": "fr", "ES": "es", "JA": "ja", "PT": "pt", "CN": "cn", "HU": "hu", "IT": "it",
               "KO": "ko", "NL": "nl", "PL": "pl", "TH": "th", "RU": "ru", "CS": "cs", "TW": "tw", "TR": "tr"}
# Sites list many regional hreflangs (en-AE -> /en-mea/, es-MX -> /latam/); the main
# language version is the first of these path segments that the page lists.
PREFERRED_SEG = {"CN": ["cn", "zh-cn", "zh"], "TW": ["tw", "zh-tw", "hk"], "RU": ["ru", "ru-cis"], "PT": ["pt", "pt-br"],
                 "ES": ["es", "es-es"], "EN": ["en", "en-us", "en-gb"]}
UAT_SEGMENT_FIX = {"ru-cis": "ru"}  # live /ru-cis/ is internal /ru/
BASE = {k.lower(): k for k in DEFAULT_SEG if k not in ("CN", "TW")}
HREFLANG_JS = "[...document.querySelectorAll('link[rel=alternate][hreflang]')].map(l => [l.hreflang, l.href])"
STATUSES = ["pending", "captured", "analysing", "done", "failed", "login"]


# ---------- registry ----------

class locked:
    def __enter__(self):
        WORK.mkdir(exist_ok=True)
        for _ in range(600):
            try:
                self.fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                if time.time() - LOCK.stat().st_mtime > 60:
                    LOCK.unlink(missing_ok=True)
                time.sleep(0.1)
        raise SystemExit("progress registry is locked")

    def __exit__(self, *a):
        os.close(self.fd)
        LOCK.unlink(missing_ok=True)


def read_reg():
    return json.loads(REG.read_text(encoding="utf-8-sig")) if REG.exists() else {"order": [], "pages": {}}


def write_reg(reg):
    tmp = REG.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(REG)


def update(slug, **fields):
    with locked():
        reg = read_reg()
        reg["pages"][slug].update(fields, updated=datetime.now().isoformat(timespec="seconds"))
        write_reg(reg)
        return reg


def bar(reg):
    pages = reg["pages"]
    n = len(reg["order"])
    c = {s: sum(1 for p in pages.values() if p["status"] == s) for s in STATUSES}
    done = c["done"]
    w = 30
    fill = round(w * done / n) if n else 0
    issues = sum(p.get("issues") or 0 for p in pages.values() if p["status"] == "done")
    return (f"[{'█' * fill}{'░' * (w - fill)}] {done}/{n} pages done ({100 * done // n if n else 0}%)  |  "
            f"{c['analysing']} analysing · {c['captured']} captured, waiting · {c['pending']} to capture · "
            f"{c['failed']} failed · {c['login']} need login  |  {issues} issues so far")


# ---------- plan ----------

def slug_of(url):
    """Path without the locale, joined with '-'. Reuses an older report named after the last segment."""
    segs = [s for s in urlparse(url).path.split("/") if s]
    if segs and re.fullmatch(r"[a-z]{2}(-[a-z]{2,4})?", segs[0].lower()):
        segs = segs[1:]
    clean = lambda s: re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")
    full = clean("-".join(segs)) or "home"
    last = clean(segs[-1]) if segs else full
    reports = Path.cwd() / "reports"
    return last if not (reports / f"{full}.md").exists() and (reports / f"{last}.md").exists() else full


def code_of(hreflang):
    h = hreflang.lower()
    if h.startswith("zh"):
        return "TW" if re.search(r"tw|hk|hant", h) else "CN"
    return BASE.get(h.split("-")[0])


def choose(links):
    """{code: live URL} from hreflang links: preferred segment, else the most used one."""
    cands = {}
    for hl, href in links:
        code = "EN" if hl.lower() == "x-default" else code_of(hl)
        segs = [s for s in urlparse(href).path.split("/") if s]
        if code and segs:
            cands.setdefault(code, []).append((segs[0].lower(), href))
    best = {}
    for code, cs in cands.items():
        segs = [s for s, _ in cs]
        pick = next((s for s in PREFERRED_SEG.get(code, [DEFAULT_SEG[code]]) if s in segs), None) \
            or max(set(segs), key=segs.count)
        best[code] = next(h for s, h in cs if s == pick)
    return best


def swap_host(url, host_url):
    h = urlparse(host_url)
    p = urlparse(url)
    segs = p.path.split("/")
    if len(segs) > 1 and segs[1] in UAT_SEGMENT_FIX:
        segs[1] = UAT_SEGMENT_FIX[segs[1]]
    return urlunparse((h.scheme, h.netloc, "/".join(segs), "", p.query, ""))


def swap_seg(url, seg):
    p = urlparse(url)
    segs = p.path.split("/")
    segs[1] = seg
    return urlunparse((p.scheme, p.netloc, "/".join(segs), "", p.query, ""))


def parse_pairs(path):
    pairs = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls = re.findall(r"https?://[^\s,;]+", line)
        if len(urls) >= 2:
            pairs.append((urls[0], urls[1]))
    return pairs


async def discover(pairs, concurrency):
    found = {}
    async with async_playwright() as p:
        browser, ctx = await open_browser(p, WIDTH)

        async def one(pair):
            page = await ctx.new_page()
            try:
                await page.goto(pair[1], wait_until="domcontentloaded", timeout=60000)
                found[pair] = await page.evaluate(HREFLANG_JS)
            except Exception as e:
                found[pair] = []
                print(f"hreflang FAILED {pair[1]}: {str(e).splitlines()[0]}", flush=True)
            finally:
                await page.close()

        await pool(pairs, one, concurrency)
        await browser.close()
    return found


def cmd_plan(pairs_file, locales, concurrency):
    pairs = parse_pairs(pairs_file)
    reg = read_reg()
    new = [pr for pr in pairs if not any(pg["uat"] == pr[0] and pg["live"] == pr[1] for pg in reg["pages"].values())]
    print(f"{len(pairs)} pages in file, {len(new)} new. Reading hreflang links...", flush=True)
    found = asyncio.run(discover(new, concurrency))
    choices = {pr: choose(found.get(pr, [])) for pr in new}
    learned = {}
    for best in choices.values():
        for code, href in best.items():
            learned.setdefault(code, [s for s in urlparse(href).path.split("/") if s][0])
    seg_of = {**DEFAULT_SEG, **learned}
    with locked():
        reg = read_reg()
        for uat, live in new:
            best = choices[(uat, live)]
            first = (urlparse(live).path.split("/") + [""])[1]
            has_seg = bool(re.fullmatch(r"[a-z]{2}(-[a-z]{2,4})?", first.lower()))
            plan_loc = {}
            for code in locales:
                if code in best:
                    lv = best[code]
                    if not urlparse(lv).query and urlparse(live).query:  # hreflang drops ?tab=… etc.
                        lv = urlunparse(urlparse(lv)._replace(query=urlparse(live).query))
                    plan_loc[code] = {"live": lv, "uat": swap_host(lv, uat), "listed": True}
                elif has_seg:
                    lv = swap_seg(live, seg_of[code])
                    plan_loc[code] = {"live": lv, "uat": swap_host(lv, uat), "listed": False}
            slug = base = slug_of(live)
            k = 2
            while slug in reg["pages"]:
                slug, k = f"{base}-{k}", k + 1
            d = WORK / slug
            d.mkdir(parents=True, exist_ok=True)
            (d / "plan.json").write_text(json.dumps({"slug": slug, "uat": uat, "live": live, "locales": plan_loc},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
            reg["order"].append(slug)
            reg["pages"][slug] = {"uat": uat, "live": live, "status": "pending", "locales": len(plan_loc),
                                  "unlisted": [c for c, v in plan_loc.items() if not v["listed"]],
                                  "updated": datetime.now().isoformat(timespec="seconds")}
            print(f"  {slug}: {len(plan_loc)} locales ({sum(v['listed'] for v in plan_loc.values())} listed on live)")
        write_reg(reg)
    print(bar(reg))


# ---------- capture ----------

async def run_capture(slugs, concurrency, shots):
    jobs, left, errors = [], {}, {s: {} for s in slugs}
    for slug in slugs:
        plan = json.loads((WORK / slug / "plan.json").read_text(encoding="utf-8-sig"))
        for code, u in plan["locales"].items():
            for side in ("uat", "live"):
                jobs.append((slug, {"name": f"{code.lower()}-{side}", "url": u[side]}))
        left[slug] = 2 * len(plan["locales"])
    total = len(slugs)
    async with async_playwright() as p:
        browser, ctx = await open_browser(p, WIDTH)

        async def one(job):
            slug, entry = job
            full = shots == "all" or (shots == "en" and entry["name"].startswith("en-"))
            line, data = await capture(ctx, entry, WORK / slug, None, full)
            if data is None:
                errors[slug][entry["name"]] = "Login needed" if "LOGIN NEEDED" in line else "Failed to load"
                print(f"  {slug} {line}", flush=True)
            left[slug] -= 1
            if left[slug] == 0:
                await asyncio.to_thread(finish, slug, errors[slug], total)

        await pool(jobs, one, concurrency)
        await browser.close()


def finish(slug, errs, total):
    plan_path = WORK / slug / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    plan["errors"] = errs
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    if any(v == "Login needed" for v in errs.values()):
        reg = update(slug, status="login")
        print(f"LOGIN NEEDED  {slug}", flush=True)
        return
    try:
        leads = diff.run(WORK / slug)
        reg = update(slug, status="captured", leads=leads, failed_loads=len(errs))
    except Exception as e:
        reg = update(slug, status="failed", note=f"diff: {e}")
    n = sum(1 for s in reg["pages"].values() if s["status"] not in ("pending", "login"))
    print(f"captured {slug} ({reg['pages'][slug].get('leads', '?')} leads)  [{n}/{len(reg['order'])} captured]", flush=True)


def cmd_capture(slugs, concurrency, shots, shard):
    reg = read_reg()
    if not slugs:
        slugs = [s for s in reg["order"] if reg["pages"][s]["status"] in ("pending", "login")]
    if shard:
        i, n = (int(x) for x in shard.split("/"))
        slugs = slugs[i - 1::n]
    print(f"Capturing {len(slugs)} pages with {concurrency} tabs...", flush=True)
    asyncio.run(run_capture(slugs, concurrency, shots))
    print(bar(read_reg()))


# ---------- tracking ----------

def cmd_next(n):
    with locked():
        reg = read_reg()
        got = [s for s in reg["order"] if reg["pages"][s]["status"] == "captured"][:n]
        for s in got:
            reg["pages"][s].update(status="analysing", updated=datetime.now().isoformat(timespec="seconds"))
        write_reg(reg)
    print("\n".join(got) if got else "(none captured yet)")


def cmd_mark(slug, status, args):
    fields = {"status": status}
    for flag, key, cast in (("--issues", "issues", int), ("--note", "note", str), ("--confluence", "confluence_url", str)):
        if flag in args:
            fields[key] = cast(args[args.index(flag) + 1])
    reg = update(slug, **fields)
    if status == "done" and "--keep" not in args:
        for f in (WORK / slug).glob("*.jpg"):
            f.unlink()
    print(bar(reg))


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda flag, default: a[a.index(flag) + 1] if flag in a else default
    cmd = a[0]
    if cmd == "plan":
        cmd_plan(a[1], [c.strip().upper() for c in opt("--locales", ",".join(diff.LOCALES)).split(",")], int(opt("--concurrency", 10)))
    elif cmd == "capture":
        s = opt("--slugs", "")
        cmd_capture([x for x in s.split(",") if x], int(opt("--concurrency", 10)), opt("--shots", "en"), opt("--shard", ""))
    elif cmd == "progress":
        print(bar(read_reg()))
    elif cmd == "next":
        cmd_next(int(a[1]))
    elif cmd == "mark":
        cmd_mark(a[1], a[2], a)
    elif cmd == "list":
        reg = read_reg()
        for s in reg["order"]:
            if len(a) < 2 or reg["pages"][s]["status"] == a[1]:
                p = reg["pages"][s]
                print(f"{p['status']:<10} {s}  issues={p.get('issues', '-')}  {p['live']}")
    else:
        print(__doc__)
