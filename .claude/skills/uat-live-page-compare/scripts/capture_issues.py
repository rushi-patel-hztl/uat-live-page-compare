"""Save an annotated UAT and live screenshot of the component behind each issue.

Usage: python capture_issues.py shots.json [--concurrency 6]

shots.json:
{
  "out": "reports/screenshots/<page-slug>",
  "width": 1440,
  "shots": [
    {"name": "5-german", "uat": "<UAT URL>", "live": "<live URL>",
     "anchor": "Heading or text inside the component",
     "anchor_uat": "optional, if the text differs on UAT",
     "anchor_live": "optional, if the text differs on live",
     "mark": "text of the element at fault (CTA label, tab, card title),
              or css:<selector> for elements without unique text (an image)",
     "mark_uat": "optional, if it differs on UAT",
     "mark_live": "optional, if it differs on live",
     "note": "the issue in one short sentence, shown on the UAT image",
     "note_live": "optional, shown on the live image (default: what live has)",
     "missing_on": "optional: 'uat' or 'live' when the component is missing there;
                    that side's anchor is then the component just above",
     "open": ["optional: titles of tabs to click / accordion items to expand, in
               order, before looking for the anchor (content hidden on load)"],
     "open_uat": [...], "open_live": [...]   (optional, if the titles differ per side),
     "in_header": "optional: true when the issue is in the header (top-right CTA);
                   the header is otherwise skipped when looking for the anchor"}
  ]
}

Each image gets:
  - a coloured outline on the element at fault (red on UAT, green on live), or
    on the whole component when there is no mark;
  - a callout next to it with the issue number and note;
  - for missing_on, a dashed box below the anchor component saying what is
    missing;
  - a caption band at the top: side, issue number, language and the note.

Writes <out>/<name>-uat.png and <out>/<name>-live.png and prints one line per
file. Headless Chrome, same viewport on both sides, sharing the saved login
with browse.py; shots run in parallel tabs. If the anchor text isn't found the top of the page is saved
and the line says ANCHOR NOT FOUND; MARK NOT FOUND means the outline went on
the anchor instead; OPEN NOT FOUND means a tab or accordion title in "open"
wasn't found to click.
"""
import asyncio
import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

from pw import load, open_browser, pool

SIDE = {"uat": ("UAT", "#E00000"), "live": ("LIVE", "#0A7D3B")}
LANGS = {"chinese-simplified": "Chinese (Simplified)", "chinese-traditional": "Chinese (Traditional)"}

# Scrolls to load lazy content, finds the component holding the anchor text,
# draws the outline, callout or missing box, and returns boxes in page
# coordinates for cropping.
ANNOTATE_JS = """
async ([anchor, mark, label, color, missing, opens, inHeader]) => {
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  for (let i = 0; i < 100; i++) { const y = scrollY; scrollBy(0, innerHeight * 0.8);
    await new Promise((r) => setTimeout(r, 120)); if (scrollY === y) break; }
  scrollTo(0, 0); await new Promise((r) => setTimeout(r, 500));
  const shown = (el) => { const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
    return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
  const excluded = (el) => (inHeader ? el.closest('footer,[role=contentinfo]') : el.closest('header,footer,nav,[role=banner],[role=contentinfo]'));
  const smallest = (root, text) => {
    const t = norm(text);
    const hits = [...root.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,a,button,span,div,img,label')]
      .filter((e) => shown(e) && !excluded(e) && (norm(e.innerText).includes(t) || norm(e.alt) === t));
    return hits.find((e) => !hits.some((o) => o !== e && e.contains(o))) || null;
  };
  // Click the tabs / expand the accordion items the issue sits in.
  const openMissing = [];
  for (const want of opens || []) {
    const ts = [...document.querySelectorAll('[role=tab],[aria-expanded],details > summary')].filter((e) => shown(e) && !excluded(e));
    const title = (e) => norm(e.innerText || e.getAttribute('aria-label'));
    const t = ts.find((e) => title(e) === norm(want)) || ts.find((e) => title(e).includes(norm(want)));
    if (!t) { openMissing.push(want); continue; }
    const det = t.tagName === 'SUMMARY' ? t.parentElement : null;
    const on = det ? det.open : t.getAttribute('aria-selected') === 'true' || t.getAttribute('aria-expanded') === 'true';
    if (!on) { t.scrollIntoView({ block: 'center' }); if (det) det.open = true; else t.click();
      await new Promise((r) => setTimeout(r, 600)); }
  }
  // What opened often lazy-loads its images: give them up to 3 s.
  if ((opens || []).length) for (let i = 0; i < 30; i++) {
    if ([...document.images].filter(shown).every((im) => im.complete && im.naturalWidth)) break;
    await new Promise((r) => setTimeout(r, 100)); }
  scrollTo(0, 0);
  const hit = smallest(document.body, anchor);
  if (!hit) return { notFound: true, openMissing };
  const heads = [...document.querySelectorAll('h1,h2')].filter((h) => shown(h) && !excluded(h));
  // Grow to the component: the anchor may sit beside its h1/h2 (an eyebrow,
  // a card), so take in one heading, then stop before reaching a second.
  let b = hit;
  while (b.parentElement && b.parentElement !== document.body && !excluded(b.parentElement)) {
    const own = heads.filter((h) => b.contains(h) || h.contains(b)).length;
    const added = heads.filter((h) => !b.contains(h) && !h.contains(b) && b.parentElement.contains(h)).length;
    if (added && (own || added > 1)) break;
    b = b.parentElement;
  }
  const box = (el) => { const r = el.getBoundingClientRect();
    return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height }; };
  const layer = (css) => { const d = document.createElement('div');
    Object.assign(d.style, { position: 'absolute', zIndex: 2147483647, boxSizing: 'border-box',
      font: 'bold 15px/1.35 Arial, sans-serif' }, css);
    document.documentElement.appendChild(d); return d; };
  const union = (a, c) => { const x = Math.min(a.x, c.x), y = Math.min(a.y, c.y);
    return { x, y, w: Math.max(a.x + a.w, c.x + c.w) - x, h: Math.max(a.y + a.h, c.y + c.h) - y }; };
  let markFound = !mark, focus;
  if (missing) {
    const r = box(b);
    const gap = layer({ left: r.x + 'px', top: r.y + r.h + 10 + 'px', width: r.w + 'px', minHeight: '64px',
      border: `3px dashed ${color}`, background: '#FFFFFFEE', color, padding: '12px',
      display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center' });
    gap.textContent = label || 'Missing here';
    focus = box(gap);
  } else {
    const pick = (m) => m.startsWith('css:') ? [...b.querySelectorAll(m.slice(4))].find(shown) || null : smallest(b, m);
    let target = mark ? pick(mark) : b;
    if (mark && target) markFound = true;
    if (!target) target = hit;
    target.style.setProperty('outline', `3px solid ${color}`, 'important');
    // Media often sits in an overflow:hidden wrapper that clips an outside outline.
    const media = /^(IMG|VIDEO|IFRAME|PICTURE|svg)$/.test(target.tagName);
    target.style.setProperty('outline-offset', media ? '-3px' : '4px', 'important');
    focus = box(target);
    if (label) {
      const tag = layer({ background: color, color: '#FFFFFF', padding: '6px 10px', borderRadius: '4px',
        maxWidth: '560px', boxShadow: '0 2px 6px rgba(0,0,0,.35)', left: '0px', top: '0px' });
      tag.textContent = label;
      const t = focus, tw = tag.offsetWidth, th = tag.offsetHeight;
      // Above the element, unless that is under the site header: then inside
      // its top edge for a large element, or below a small one.
      const hdr = [...document.querySelectorAll('header,[role=banner]')].filter(shown)
        .reduce((m, h) => Math.max(m, h.getBoundingClientRect().bottom + scrollY), 0);
      let top = t.y - th - 12;
      if (top < hdr + 4) top = t.h > 200 ? t.y + 12 : t.y + t.h + 12;
      tag.style.top = top + 'px';
      tag.style.left = Math.max(8, Math.min(t.x, document.documentElement.clientWidth - tw - 8)) + 'px';
      focus = union(focus, box(tag));
    }
  }
  return { block: box(b), focus, markFound, openMissing };
}
"""

MAX_H = 1600


def font(size, bold=False):
    for name in (["ModernEra-Bold.otf", "arialbd.ttf"] if bold else ["ModernEra-Regular.otf", "arial.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def clip_for(found, width):
    block, focus = found["block"], found["focus"]
    if block["h"] <= MAX_H:
        top, bottom = min(block["y"], focus["y"]), max(block["y"] + block["h"], focus["y"] + focus["h"])
    else:
        top = min(focus["y"], max(block["y"], focus["y"] - 300))
        bottom = max(min(top + 1200, block["y"] + block["h"]), focus["y"] + focus["h"])
    top = max(0, top - 40)
    return {"x": 0, "y": top, "width": width, "height": bottom - top + 40}


def add_caption(path, head, note, color):
    img = Image.open(path).convert("RGB")
    f_head, f_note = font(20, bold=True), font(17)
    lines = textwrap.wrap(note, width=max(40, img.width // 10)) if note else []
    band = 18 + 26 + 24 * len(lines) + 14
    out = Image.new("RGB", (img.width, img.height + band), "#FFFFFF")
    out.paste(img, (0, band))
    d = ImageDraw.Draw(out)
    d.rectangle([0, 0, img.width, band - 1], fill="#1F1F1F")
    d.rectangle([0, 0, 10, band - 1], fill=color)
    d.text((26, 16), head, font=f_head, fill="#FFFFFF")
    for i, line in enumerate(lines):
        d.text((26, 46 + 24 * i), line, font=f_note, fill="#E8E8E8")
    out.save(path)


async def capture(ctx, url, anchor, mark, label, color, missing, opens, in_header, path, width):
    page = await ctx.new_page()
    try:
        _, need_login = await load(page, url)
        if need_login:
            return f"{path}  LOGIN NEEDED: {page.url}"
        found = await page.evaluate(ANNOTATE_JS, [anchor, mark, label, color, missing, opens, in_header])
        extra = f"  OPEN NOT FOUND: {found['openMissing']!r}" if found["openMissing"] else ""
        if not found.get("notFound"):
            await page.screenshot(path=path, full_page=True, clip=clip_for(found, width))
            return (path if found["markFound"] else f"{path}  MARK NOT FOUND: {mark!r}") + extra
        await page.screenshot(path=path)
        return f"{path}  ANCHOR NOT FOUND: {anchor!r} on {url}{extra}"
    finally:
        await page.close()


def jobs_of(spec, out):
    for shot in spec["shots"]:
        num, _, lang = shot["name"].partition("-")
        num = shot.get("issue", num)
        lang = shot.get("language") or LANGS.get(lang, lang.replace("-", " ").title())
        for side in ("uat", "live"):
            if shot.get(side):
                yield shot, side, num, lang


async def main(spec_path, concurrency):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8-sig"))
    out = Path(spec["out"])
    out.mkdir(parents=True, exist_ok=True)
    width = spec.get("width", 1440)
    async with async_playwright() as p:
        browser, ctx = await open_browser(p, width)

        async def one(job):
            shot, side, num, lang = job
            word, color = SIDE[side]
            note = shot.get("note", "") if side == "uat" else shot.get("note_live") or "Live: expected"
            missing = shot.get("missing_on") == side
            anchor = shot.get(f"anchor_{side}") or shot["anchor"]
            mark = None if missing else (shot.get(f"mark_{side}") or shot.get("mark"))
            opens = shot.get(f"open_{side}") or shot.get("open") or []
            label = f"#{num}  {note}" if (shot.get("note") or missing) else None
            path = str(out / f"{shot['name']}-{side}.png")
            try:
                line = await capture(ctx, shot[side], anchor, mark, label, color, missing, opens, bool(shot.get("in_header")), path, width)
                if "LOGIN NEEDED" not in line:
                    await asyncio.to_thread(add_caption, path, f"{word}  |  Issue #{num}  |  {lang}", note, color)
                print(line, flush=True)
            except Exception as e:
                print(f"{path}  FAILED: {e}".splitlines()[0], flush=True)

        await pool(list(jobs_of(spec, out)), one, concurrency)
        await browser.close()


if __name__ == "__main__":
    conc = int(sys.argv[sys.argv.index("--concurrency") + 1]) if "--concurrency" in sys.argv else 6
    asyncio.run(main(sys.argv[1], conc))
