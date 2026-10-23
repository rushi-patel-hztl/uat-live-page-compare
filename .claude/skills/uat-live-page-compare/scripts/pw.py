"""Shared Playwright setup for batch.py, browse.py and capture_issues.py.

All headless runs use the installed Chrome in a plain (non-persistent) context
loaded with the cookies saved in .playwright-profile/state.json, so any number
of scripts can run at the same time. The login window (browse.py --login)
uses the persistent profile in .playwright-profile/ and keeps state.json up to
date while it is open.
"""
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252
PROFILE = Path.cwd() / ".playwright-profile"  # the scripts are run from the project folder
STATE = PROFILE / "state.json"

HIDE_CSS = """
#onetrust-consent-sdk, #onetrust-banner-sdk, .onetrust-pc-dark-filter,
#CybotCookiebotDialog, .modal-backdrop { display: none !important; }
html, body { overflow: visible !important; }
"""
# visible, not auto: undoes a modal's scroll lock without turning a fixed-height
# <body> into its own scroll area (then scrollY stays 0 and screenshots are cut).

# Closes pop-ups (region modal etc.) with their X, then hides any full-screen
# overlay that is still showing. Cookie banners are hidden, never accepted.
DISMISS_JS = """
() => {
  const big = (e) => { const cs = getComputedStyle(e); const r = e.getBoundingClientRect();
    return cs.position === 'fixed' && cs.display !== 'none' && cs.visibility !== 'hidden'
      && r.width >= innerWidth * 0.5 && r.height >= innerHeight * 0.5; };
  const overlays = [...document.querySelectorAll('body *')].filter(big);
  overlays.forEach((o) => {
    const x = [...o.querySelectorAll('button,[role=button],a')].find((b) =>
      /close|schlie|fermer|cerrar|chiudi|fechar|sluiten|zamknij/i.test(b.getAttribute('aria-label') || '')
      || /close/i.test(String(b.className)) || /^[x×✕]?$/i.test((b.innerText || '').trim()));
    if (x) x.click();
  });
  return new Promise((r) => setTimeout(() => {
    [...document.querySelectorAll('body *')].filter(big).forEach((o) => o.style.setProperty('display', 'none', 'important'));
    r(overlays.length);
  }, 600));
}
"""

PASSWORD_JS = "() => [...document.querySelectorAll('input[type=password]')].some((e) => e.offsetParent)"
LOGIN_URL = re.compile(r"login|signin|sign-in|sso|oauth|/auth|okta|microsoftonline|adfs", re.I)


async def open_browser(p, width):
    """Headless Chrome + one context with the saved login. Returns (browser, ctx)."""
    try:
        browser = await p.chromium.launch(channel="chrome", headless=True)
    except Exception as e:
        raise SystemExit(f"Could not start Chrome ({str(e).splitlines()[0]}).")
    ctx = await browser.new_context(viewport={"width": width, "height": 900},
                                    storage_state=str(STATE) if STATE.exists() else None)
    extra = _extra_headers()
    if extra:
        async def add_headers(route):
            host = urlparse(route.request.url).hostname or ""
            if host == "teamviewer.com" or host.endswith(".teamviewer.com"):
                await route.continue_(headers={**route.request.headers, **extra})
            else:
                await route.continue_()
        await ctx.route("**/*", add_headers)
    return browser, ctx


def _extra_headers():
    """Optional request headers (one 'Name: value' per line) from work/_header.txt, sent only to teamviewer.com hosts."""
    f = Path.cwd() / "work" / "_header.txt"
    out = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            if ":" in line and not line.lstrip().startswith("#"):
                k, v = line.split(":", 1)
                if k.strip() and v.strip():
                    out[k.strip()] = v.strip()
    return out


async def load(page, url):
    """Open url, hide cookie banners, close pop-ups. Returns (status, login_needed)."""
    resp = await page.goto(url, wait_until="load", timeout=60000)
    try:
        await page.wait_for_load_state("networkidle", timeout=4000)
    except Exception:
        pass
    await page.wait_for_timeout(800)
    moved = urlparse(page.url).hostname != urlparse(url).hostname
    if await page.evaluate(PASSWORD_JS) or (moved and LOGIN_URL.search(page.url)):
        return (resp.status if resp else None), True
    await page.add_style_tag(content=HIDE_CSS)
    await page.evaluate(DISMISS_JS)
    return (resp.status if resp else None), False


async def pool(items, worker, concurrency):
    """Run worker(item) for every item with at most `concurrency` at once, in order."""
    queue = asyncio.Queue()
    for it in items:
        queue.put_nowait(it)

    async def run():
        while not queue.empty():
            await worker(queue.get_nowait())

    await asyncio.gather(*(run() for _ in range(max(1, min(concurrency, len(items))))))


def login(url):
    """Visible Chrome on the persistent profile; saves cookies to state.json until closed."""
    from playwright.sync_api import sync_playwright
    PROFILE.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE), channel="chrome", headless=False,
                                                   viewport={"width": 1440, "height": 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="load", timeout=60000)
        print("Login window open. Log in there, then close the window.", flush=True)
        while True:
            try:
                ctx.storage_state(path=str(STATE))
                if page.is_closed():
                    break
                page.wait_for_timeout(2000)
            except Exception:
                break
        try:
            ctx.close()
        except Exception:
            pass
    print(f"Window closed; the login is saved in {STATE}.")
