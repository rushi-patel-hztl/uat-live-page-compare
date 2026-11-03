"""Capture the current www version of every page in all 17 locales.

  python capture.py OLD_DATA.json TABS [--missing] [WORK=work/_golive]

Writes WORK/<slug>/<CODE>-now.txt|.json (EN also gets screenshot slices).
Pages with no issues are skipped. --missing only loads locales with no <CODE>-now.json yet.
"""
import asyncio, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / '.claude/skills/uat-live-page-compare/scripts'))
from browse import capture
from pw import open_browser, pool
from playwright.async_api import async_playwright

CODES = ["EN", "DE", "FR", "ES", "JA", "PT", "CN", "HU", "IT", "KO", "NL", "PL", "TH", "RU", "CS", "TW", "TR"]
seg = lambda c: "ru-cis" if c == "RU" else c.lower()   # old site's main locale segments
args = [a for a in sys.argv[1:] if not a.startswith('--')]
data, conc = args[0], int(args[1])
work = ROOT / (args[2] if len(args) > 2 else 'work/_golive')
only_missing = '--missing' in sys.argv


async def main():
    d = json.load(open(data, encoding='utf8'))
    items = []
    for p in d['pages']:
        if not p['issues']:
            continue
        out = work / p['slug']
        out.mkdir(parents=True, exist_ok=True)
        for c in CODES:
            if only_missing and (out / f"{c}-now.json").exists():
                continue
            items.append((p['slug'], out, c, p['live'].replace('/en/', f'/{seg(c)}/', 1)))
    print(len(items), 'loads', flush=True)
    async with async_playwright() as pl:
        browser, ctx = await open_browser(pl, 1440)

        async def work_one(it):
            slug, out, c, url = it
            line, _ = await capture(ctx, {"name": f"{c}-now", "url": url}, out, None, shots=(c == "EN"))
            print(slug, line, flush=True)
        await pool(items, work_one, conc)
        await browser.close()

asyncio.run(main())
