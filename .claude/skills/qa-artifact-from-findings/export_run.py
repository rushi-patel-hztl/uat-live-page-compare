"""Pack the results of a uat-live-page-compare run into one zip to send to a teammate (or to merge machines).

Run from the project folder:
  py -3.13 <skill>/export_run.py my-run.zip --slugs-file work/pairs.txt
  py -3.13 <skill>/export_run.py my-run.zip --prefix solutions
Contains, for each page: work/<slug>/findings.json + plan.json, reports/<slug>.md, reports/screenshots/<slug>/.
The receiver unzips it into their own project folder (same layout), then runs build.py over the combined pages.
"""
import argparse, json, pathlib, re, sys, zipfile
from urllib.parse import urlparse

ap = argparse.ArgumentParser()
ap.add_argument("zipfile")
ap.add_argument("--slugs", default="")
ap.add_argument("--slugs-file", default="")
ap.add_argument("--prefix", default="")
a = ap.parse_args()
W = pathlib.Path(".")


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
n = 0
with zipfile.ZipFile(a.zipfile, "w", zipfile.ZIP_DEFLATED) as z:
    for s in slugs:
        if not (W / "work" / s / "findings.json").exists():
            continue
        for f in (W / "work" / s / "findings.json", W / "work" / s / "plan.json", W / "reports" / f"{s}.md"):
            if f.exists():
                z.write(f, f.as_posix())
        for f in (W / "reports" / "screenshots" / s).glob("*"):
            z.write(f, f.as_posix())
        n += 1
if not n:
    sys.exit("No pages with findings found.")
print(f"{n} pages -> {a.zipfile}")
