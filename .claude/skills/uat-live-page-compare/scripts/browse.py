"""Open pages in Chrome with Playwright, snapshot them with extract.js and save
full-page screenshots. batch.py uses the same capture for whole page lists;
run this directly for one-off checks.

Usage:
  python browse.py pages.json [--concurrency 8]   capture every page (headless, in parallel)
  python browse.py --login <url>                  visible Chrome window so the user can log in;
                                                  waits until it is closed

pages.json:
{
  "out": "<folder>",
  "width": 1440,
  "opts": {"anchors": "h1,h2,h3", "exclude": [".site-header"]},   (optional)
  "pages": [
    {"name": "en-uat", "url": "<UAT URL>",
     "js": "optional expression to measure something; its result is printed"}
  ]
}

For each page writes <out>/<name>.txt (readable snapshot), <name>.json
(structured snapshot for diff.py) and the full page as <name>-01.jpg, -02.jpg,
... in 1400px slices so each one is readable when opened. Prints one line per
page with HTTP status, final URL and the number of slices, or LOGIN NEEDED /
FAILED.
"""
import asyncio
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

from pw import DISMISS_JS, load, login, open_browser, pool

SLICE_H = 1400
# extract.js is written for pasting as `await (async () => {...})();`.
EXTRACT = re.sub(r"^\s*//.*$", "", (Path(__file__).parent / "extract.js").read_text(encoding="utf-8"), flags=re.M)
EXTRACT = EXTRACT.strip().removeprefix("await").strip().rstrip(";")


def save_slices(png, base):
    img = Image.open(io.BytesIO(png)).convert("RGB")
    n = 0
    for n, top in enumerate(range(0, img.height, SLICE_H), 1):
        img.crop((0, top, img.width, min(top + SLICE_H, img.height))).save(f"{base}-{n:02d}.jpg", quality=72)
    return n


async def capture(ctx, entry, out, opts, shots=True):
    """Capture one page. Returns (line, data) where data is the structured snapshot or None."""
    name, url = entry["name"], entry["url"]
    page = await ctx.new_page()
    try:
        status, need_login = await load(page, url)
        if need_login:
            return f"{name}  LOGIN NEEDED: {page.url}", None
        if opts:
            await page.evaluate("(o) => { window.__CMP_OPTS = o; }", opts)
        await page.evaluate(EXTRACT)
        await page.evaluate(DISMISS_JS)  # pop-ups that only open on scroll
        data = await page.evaluate("() => window.__cmpData")
        data["status"] = status
        (out / f"{name}.txt").write_text(await page.evaluate("() => window.__cmpOut"), encoding="utf-8")
        (out / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        slices = 0
        if shots:
            # Some sites scroll to a ?tab=… target on load or after a tab click;
            # a full-page shot taken while scrolled starts mid-page.
            await page.evaluate("() => { scrollTo({top: 0, left: 0, behavior: 'instant'});"
                                " document.body.scrollTop = 0; document.documentElement.scrollTop = 0; }")
            await page.wait_for_timeout(500)
            slices = await asyncio.to_thread(save_slices, await page.screenshot(full_page=True), out / name)
        line = f"{name}  {status}  {page.url}  {slices} slices"
        if entry.get("js"):
            line += f"\n  js: {json.dumps(await page.evaluate(entry['js']), ensure_ascii=False)[:2000]}"
        return line, data
    except Exception as e:
        return f"{name}  FAILED: {e}".splitlines()[0], None
    finally:
        await page.close()


async def main(spec_path, concurrency):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8-sig"))
    out = Path(spec["out"])
    out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser, ctx = await open_browser(p, spec.get("width", 1440))

        async def one(entry):
            line, _ = await capture(ctx, entry, out, spec.get("opts"))
            print(line, flush=True)

        await pool(spec["pages"], one, concurrency)
        await browser.close()


if __name__ == "__main__":
    if sys.argv[1] == "--login":
        login(sys.argv[2])
    else:
        conc = int(sys.argv[sys.argv.index("--concurrency") + 1]) if "--concurrency" in sys.argv else 8
        asyncio.run(main(sys.argv[1], conc))
