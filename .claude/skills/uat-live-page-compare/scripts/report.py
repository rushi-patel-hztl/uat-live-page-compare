"""Render reports from findings.json files.

Usage (run from the project folder):
  python report.py page <slug>    reports/<slug>.md (new dated section on top) and
                                  work/<slug>/confluence.html (body for the page's Confluence page)
  python report.py common         reports/_common-issues.md and work/_index.html (body for the
                                  Confluence index page: progress, every page, common issues)

work/<slug>/findings.json:
{
  "title": "Webinar: Strengthening security foundations",
  "scope": "All 17 locales",
  "coverage": [{"language": "English", "uat": "...", "live": "...", "uat_status": "Loads",
                "live_status": "Loads", "lang_ok": "Yes"}],          (or omit: taken from diff.json)
  "issues": [{"id": 1, "component": "Hero", "kind": "CTA",
              "issue": "Primary CTA is outlined blue, live is filled navy",
              "uat": "#2F5BEA outline", "live": "#050A52 fill",
              "languages": ["English", "German"],
              "shots": {"uat": "screenshots/<slug>/1-english-uat.png", "live": "screenshots/<slug>/1-english-live.png"},
              "cause": "Button variant not mapped", "signature": "ctastyle:#2F5BEA>#050A52"}],
  "not_issues": ["one line each"],
  "couldnt_check": ["one line each"]
}
"""
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
WORK, REPORTS = ROOT / "work", ROOT / "reports"
EXCLUDED = ("header top-bar links (the menu items and header CTA are checked, at 1440px), mega-menu contents, footer, font size, font weight, body text #2D2D2D vs #545454, lang code variants, "
            "the RU → ru-cis redirect, card/column widths on their own, and links that reach the same page")
COLS = ["#", "Languages", "Component", "Issue", "UAT", "Live", "UAT screenshot", "Live screenshot",
        "Likely cause", "Suggested owner", "User to confirm"]


def today():
    return datetime.now().strftime("%d %B %Y")


def cell(s):
    return str(s or "").replace("|", "\\|").replace("\n", " ")


def langs(i, total):
    ls = i.get("languages") or []
    return ", ".join(ls) + (f" ({len(ls)}/{total})" if len(ls) > 1 else "")


def load(slug):
    d = WORK / slug
    f = json.loads((d / "findings.json").read_text(encoding="utf-8-sig"))
    plan = json.loads((d / "plan.json").read_text(encoding="utf-8-sig"))
    if not f.get("coverage") and (d / "diff.json").exists():
        f["coverage"] = json.loads((d / "diff.json").read_text(encoding="utf-8-sig"))["coverage"]
    return f, plan


def page_md(slug, f, plan):
    cov, issues = f.get("coverage", []), f.get("issues", [])
    n = len(cov) or len(plan["locales"])
    out = [f"## {today()} ({f.get('scope') or f'{n} locales'})", "",
           f"- **Internal:** {plan['uat']}", f"- **Live:** {plan['live']}",
           f"- **Excluded:** {EXCLUDED}.", "", "### Pages checked", "",
           "| Language | UAT URL | Live URL | Internal | Live | Content language matches live? |", "|---|---|---|---|---|---|"]
    out += [f"| {c['language']} | {c['uat']} | {c['live']} | {cell(c['uat_status'])} | {cell(c['live_status'])} | {cell(c['lang_ok'])} |" for c in cov]
    out += ["", "### Issues", "", "| " + " | ".join(COLS) + " |", "|" + "---|" * len(COLS)]
    for i in issues:
        sh = i.get("shots") or {}
        link = lambda p: f"[{Path(p).name}]({p})" if p else "Not captured"
        out.append("| " + " | ".join(cell(x) for x in [i["id"], langs(i, n), i.get("component"), i.get("issue"), i.get("uat"),
                                                        i.get("live"), link(sh.get("uat")), link(sh.get("live")), i.get("cause"), "", ""]) + " |")
    nl = len({l for i in issues for l in i.get("languages", [])})
    out += ["", f"**{len(issues)} issues across {nl} of {n} languages.** An issue seen in several languages is one row "
                "listing them all. Likely causes are suggestions for the team to confirm.", ""]
    common = [i for i in issues if i.get("also_on")]
    if common:
        out += ["### Also seen on other pages", ""] + [f"- #{i['id']} {i['issue']}: also on {', '.join(i['also_on'][:10])}"
                                                       + (f" and {len(i['also_on']) - 10} more" if len(i['also_on']) > 10 else "") for i in common] + [""]
    out += ["### Possibly not an issue", ""] + [f"- {x}" for x in f.get("not_issues") or ["None."]] + [""]
    out += ["### Couldn't check", ""] + [f"- {x}" for x in f.get("couldnt_check") or ["Nothing."]] + [""]
    return "\n".join(out)


def page_html(slug, f, plan):
    e = lambda s: html.escape(str(s or ""))
    cov, issues = f.get("coverage", []), f.get("issues", [])
    n = len(cov) or len(plan["locales"])
    h = [f"<p><strong>Checked:</strong> {today()}  |  <strong>Internal:</strong> <a href=\"{e(plan['uat'])}\">{e(plan['uat'])}</a>  |  "
         f"<strong>Live:</strong> <a href=\"{e(plan['live'])}\">{e(plan['live'])}</a></p>",
         f"<p><strong>{len(issues)} issues</strong> across {len({l for i in issues for l in i.get('languages', [])})} of {n} languages. "
         f"Excluded: {e(EXCLUDED)}.</p>", "<h2>Issues</h2><table><tbody><tr>"
         + "".join(f"<th>{c}</th>" for c in COLS if c not in ("UAT screenshot", "Live screenshot")) + "<th>Screenshots</th></tr>"]
    for i in issues:
        sh = i.get("shots") or {}
        shots = "<br/>".join(e(Path(p).name) for p in (sh.get("uat"), sh.get("live")) if p) or "Not captured"
        h.append("<tr>" + "".join(f"<td>{e(x)}</td>" for x in [i["id"], langs(i, n), i.get("component"), i.get("issue"), i.get("uat"),
                                                              i.get("live"), i.get("cause"), "", ""]) + f"<td>{shots}</td></tr>")
    h.append("</tbody></table><h2>Pages checked</h2><table><tbody><tr><th>Language</th><th>UAT URL</th><th>Live URL</th>"
             "<th>Internal</th><th>Live</th><th>Content language matches live?</th></tr>")
    h += [f"<tr><td>{e(c['language'])}</td><td>{e(c['uat'])}</td><td>{e(c['live'])}</td><td>{e(c['uat_status'])}</td>"
          f"<td>{e(c['live_status'])}</td><td>{e(c['lang_ok'])}</td></tr>" for c in cov]
    h.append("</tbody></table>")
    for title, key, empty in (("Possibly not an issue", "not_issues", "None."), ("Couldn't check", "couldnt_check", "Nothing.")):
        h.append(f"<h2>{title}</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in f.get(key) or [empty]) + "</ul>")
    return "\n".join(h)


def cmd_page(slug):
    f, plan = load(slug)
    REPORTS.mkdir(exist_ok=True)
    md_path = REPORTS / f"{slug}.md"
    section = page_md(slug, f, plan)
    if md_path.exists():
        old = md_path.read_text(encoding="utf-8")
        head, _, rest = old.partition("\n")
        md_path.write_text(f"{head}\n\n{section}\n{rest.lstrip()}" if head.startswith("# ") else f"{section}\n{old}", encoding="utf-8")
    else:
        md_path.write_text(f"# {f.get('title') or slug}, internal vs live\n\n{section}", encoding="utf-8")
    (WORK / slug / "confluence.html").write_text(page_html(slug, f, plan), encoding="utf-8")
    print(f"{md_path}  ({len(f.get('issues', []))} issues)\n{WORK / slug / 'confluence.html'}")


def key_of(i):
    sig = i.get("signature")
    if sig:
        return re.sub(r":\d+(?=[:>]|$)", "", sig)  # drop block positions so the same fault on any page groups
    return f"{i.get('kind', '')}|{re.sub(r'[^a-z0-9#]+', ' ', (i.get('issue') or '').lower()).strip()}"


def cmd_common():
    reg = json.loads((WORK / "_progress.json").read_text(encoding="utf-8-sig")) if (WORK / "_progress.json").exists() else {"order": [], "pages": {}}
    groups = {}
    for slug in reg["order"]:
        fp = WORK / slug / "findings.json"
        if reg["pages"][slug]["status"] != "done" or not fp.exists():
            continue
        for i in json.loads(fp.read_text(encoding="utf-8-sig")).get("issues", []):
            g = groups.setdefault(key_of(i), {"issue": i.get("issue"), "kind": i.get("kind", ""), "uat": i.get("uat"),
                                              "live": i.get("live"), "cause": i.get("cause"), "pages": {}, "langs": set()})
            g["pages"][slug] = i["id"]
            g["langs"].update(i.get("languages", []))
    common = sorted((g for g in groups.values() if len(g["pages"]) > 1), key=lambda g: -len(g["pages"]))
    # tell each page which of its issues are common (shown in its next report)
    for g in common:
        for slug, iid in g["pages"].items():
            fp = WORK / slug / "findings.json"
            f = json.loads(fp.read_text(encoding="utf-8-sig"))
            for i in f["issues"]:
                if i["id"] == iid:
                    i["also_on"] = [s for s in g["pages"] if s != slug]
            fp.write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding="utf-8")
    done = [s for s in reg["order"] if reg["pages"][s]["status"] == "done"]
    md = [f"# Common issues across pages", "", f"Updated {today()}. {len(done)}/{len(reg['order'])} pages done; "
          f"{len(common)} issues appear on more than one page (fix once, fixes many).", "",
          "| # | Issue | Kind | UAT | Live | Pages | Languages | Likely cause | Page (issue #) |", "|---|---|---|---|---|---|---|---|---|"]
    for n, g in enumerate(common, 1):
        pages = ", ".join(f"[{s}]({s}.md) (#{i})" for s, i in list(g["pages"].items())[:30]) + (" …" if len(g["pages"]) > 30 else "")
        md.append(f"| C{n} | {cell(g['issue'])} | {cell(g['kind'])} | {cell(g['uat'])} | {cell(g['live'])} | {len(g['pages'])} | "
                  f"{len(g['langs'])} | {cell(g['cause'])} | {pages} |")
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "_common-issues.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    e = lambda s: html.escape(str(s or ""))
    counts = {s: sum(1 for p in reg["pages"].values() if p["status"] == s) for s in ("done", "analysing", "captured", "pending", "failed", "login")}
    h = [f"<p><strong>Progress:</strong> {counts['done']}/{len(reg['order'])} pages done · {counts['analysing']} analysing · "
         f"{counts['captured'] + counts['pending']} waiting · {counts['failed']} failed · {counts['login']} need login. Updated {today()}.</p>",
         "<h2>Common issues (on more than one page)</h2><table><tbody><tr><th>#</th><th>Issue</th><th>Kind</th><th>UAT</th><th>Live</th>"
         "<th>Pages</th><th>Languages</th><th>Likely cause</th><th>Pages (issue #)</th></tr>"]
    h += [f"<tr><td>C{n}</td><td>{e(g['issue'])}</td><td>{e(g['kind'])}</td><td>{e(g['uat'])}</td><td>{e(g['live'])}</td>"
          f"<td>{len(g['pages'])}</td><td>{len(g['langs'])}</td><td>{e(g['cause'])}</td>"
          f"<td>{e(', '.join(f'{s} (#{i})' for s, i in g['pages'].items()))}</td></tr>" for n, g in enumerate(common, 1)]
    h.append("</tbody></table><h2>Pages</h2><table><tbody><tr><th>Page</th><th>Status</th><th>Issues</th><th>Live URL</th></tr>")
    for s in reg["order"]:
        p = reg["pages"][s]
        name = f"<a href=\"{e(p['confluence_url'])}\">{e(s)}</a>" if p.get("confluence_url") else e(s)
        h.append(f"<tr><td>{name}</td><td>{e(p['status'])}</td><td>{e(p.get('issues', ''))}</td><td>{e(p['live'])}</td></tr>")
    h.append("</tbody></table>")
    (WORK / "_index.html").write_text("\n".join(h), encoding="utf-8")
    print(f"{REPORTS / '_common-issues.md'}  ({len(common)} common issues)\n{WORK / '_index.html'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.argv[1] == "page":
        cmd_page(sys.argv[2])
    elif sys.argv[1] == "common":
        cmd_common()
    else:
        print(__doc__)
