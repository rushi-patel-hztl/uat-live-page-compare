"""One-time prerequisite check. Prints OK/FAIL per item; exit code 1 if anything fails.

Usage: python check_prereqs.py
"""
import sys
from pathlib import Path

ok = True


def item(name, fn):
    global ok
    try:
        print(f"OK    {name}: {fn()}")
    except Exception as e:
        ok = False
        print(f"FAIL  {name}: {str(e).splitlines()[0]}")


def chrome():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        v = b.version
        b.close()
    return f"Chrome {v}"


def writable():
    for d in ("reports", "work"):
        Path(d).mkdir(exist_ok=True)
        (Path(d) / ".write-test").write_text("x")
        (Path(d) / ".write-test").unlink()
    return "reports/ and work/"


item("Python >= 3.10", lambda: sys.version.split()[0] if sys.version_info >= (3, 10) else (_ for _ in ()).throw(RuntimeError(sys.version)))
item("Playwright", lambda: __import__("importlib.metadata").metadata.version("playwright"))
item("Pillow", lambda: __import__("PIL").__version__)
item("Installed Chrome launches", chrome)
item("Folders writable", writable)
item("Saved login", lambda: "present" if (Path(".playwright-profile") / "state.json").exists() else "none yet (only needed for pages behind a login)")
print("ALL OK" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
