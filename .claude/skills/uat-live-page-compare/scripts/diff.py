"""Machine pre-comparison of one page's UAT and live snapshots, all locales.

Usage: python diff.py <work/<slug>>

Reads <dir>/plan.json and the <code>-uat.json / <code>-live.json snapshots
written by batch.py (or browse.py), pairs the components by heading (and,
inside them, each clicked tab and expanded accordion item), and writes:
  <dir>/diff.md    readable leads, grouped across locales (same values = one lead)
  <dir>/diff.json  the same as data
Leads are candidates, not findings: confirm each on screen before reporting.
The standing exclusions (font size/weight, #2D2D2D vs #545454 body text,
lang code variants, RU -> ru-cis redirect, card/column widths, CTA widths,
spacing <= 2px, header top-bar links #050A52 vs #141414, the UAT-only "Company"
header link) are applied here so they never show up as leads.
"""
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

LOCALES = ["EN", "DE", "FR", "ES", "JA", "PT", "CN", "HU", "IT", "KO", "NL", "PL", "TH", "RU", "CS", "TW", "TR"]
NAMES = {"EN": "English", "DE": "German", "FR": "French", "ES": "Spanish", "JA": "Japanese", "PT": "Portuguese",
         "CN": "Chinese (Simplified)", "HU": "Hungarian", "IT": "Italian", "KO": "Korean", "NL": "Dutch",
         "PL": "Polish", "TH": "Thai", "RU": "Russian", "CS": "Czech", "TW": "Chinese (Traditional)", "TR": "Turkish"}
IGNORED_COLOURS = {("#2D2D2D", "#545454")}  # accepted body text colour (UAT, live)
IGNORED_HEADER_COLOURS = {("#050A52", "#141414")}  # accepted header top-bar link colour (UAT, live)
EXPECTED_HEADER_EXTRA = {"company"}  # header links that are on UAT only by design
NON_LATIN = {"JA": r"[぀-ヿ一-鿿]", "CN": r"[一-鿿]", "TW": r"[一-鿿]",
             "KO": r"[가-힯]", "TH": r"[฀-๿]", "RU": r"[Ѐ-ӿ]"}


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def words(s):
    return re.findall(r"\w+", (s or "").lower())


def sim(a, b):
    a, b = set(words(a)), set(words(b))
    return len(a & b) / len(a | b) if a and b else (1.0 if a == b else 0.0)


def page_text(d):
    return " ".join(b["txt"] for b in d["blocks"]) if d else ""


def colour_ok(u, l):
    return u == l or (u, l) in IGNORED_COLOURS


def href_key(h):
    p = urlparse(h or "")
    segs = [s for s in p.path.lower().split("/") if s]
    if segs and re.fullmatch(r"[a-z]{2}(-[a-z]{2,4})?", segs[0]):
        segs = segs[1:]  # locale segment
    return "/".join(segs) + ("#" + p.fragment if p.fragment else "")


def pair_blocks(ub, lb):
    """Pairs of (uat_index|None, live_index|None) in page order."""
    uh, lh = [norm(b["head"]) for b in ub], [norm(b["head"]) for b in lb]
    out = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, uh, lh, autojunk=False).get_opcodes():
        if op == "equal":
            out += [(i1 + k, j1 + k) for k in range(i2 - i1)]
            continue
        us, ls = list(range(i1, i2)), list(range(j1, j2))
        while us and ls:  # fuzzy pairing inside a replace run
            best = max(((SequenceMatcher(None, uh[u], lh[l]).ratio(), u, l) for u in us for l in ls))
            if best[0] < 0.6:
                break
            out.append((best[1], best[2]))
            us.remove(best[1]); ls.remove(best[2])
        out += [(u, None) for u in us] + [(None, l) for l in ls]
    return sorted(out, key=lambda p: (p[1] if p[1] is not None else (p[0] or 0) - 0.5, p[0] or 0))


def text_changes(u, l, limit=3, cap=120):
    """Changed snippets (uat, live). Text that only moved is dropped; CJK/Thai compared by character."""
    u, l = u or "", l or ""
    chars = len(u.split()) * 12 < len(u)  # few spaces: compare characters
    ut, lt = (list(u), list(l)) if chars else (u.split(), l.split())
    sm = SequenceMatcher(None, ut, lt, autojunk=False)
    if sm.ratio() >= 0.95:
        return []
    j = "" if chars else " "
    ops = [(j.join(ut[i1:i2]), j.join(lt[j1:j2])) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
    removed, added = {a.strip() for a, _ in ops if a.strip()}, {b.strip() for _, b in ops if b.strip()}
    ops = [(a, b) for a, b in ops if not ((a.strip() in added and not b.strip()) or (b.strip() in removed and not a.strip()))]
    ops = [(a, b) for a, b in ops if len(re.sub(r"\W", "", a + b)) > 1]  # punctuation-only changes
    short = lambda s: (s[:cap] + "…" if len(s) > cap else s) or "(nothing)"
    return [(short(a), short(b)) for a, b in ops[:limit]]


def compare_locale(code, u, l, add):
    """add(sig, kind, component, summary, uat, live) for every lead in this locale."""
    if not u or not l:
        return
    pairs = pair_blocks(u["blocks"], l["blocks"])
    for ui, li in pairs:
        if li is None:
            b = u["blocks"][ui]
            dup = any(norm(o["head"]) == norm(b["head"]) for k, o in enumerate(u["blocks"]) if k != ui)
            add(f"extra:{'dup' if dup else 'x'}:{ui}", "Duplicated component" if dup else "Extra component",
                b["head"], "Duplicated on UAT" if dup else "On UAT, not on live", b["head"], "-")
            continue
        lb = l["blocks"][li]
        comp = f'{lb["head"][:60]} (live #{li})'
        if ui is None:
            add(f"missing:{li}", "Missing component", comp, "On live, not on UAT", "-", lb["head"])
            continue
        ub = u["blocks"][ui]
        if not colour_ok(ub["headColor"], lb["headColor"]):
            add(f"headcolor:{li}:{ub['headColor']}>{lb['headColor']}", "Colour", comp, "Heading colour differs", ub["headColor"], lb["headColor"])
        if ub["headAlign"] != lb["headAlign"]:
            add(f"headalign:{li}:{ub['headAlign']}>{lb['headAlign']}", "Alignment", comp, "Heading alignment differs", ub["headAlign"], lb["headAlign"])
        if ub["bg"] != lb["bg"]:
            add(f"bg:{li}:{ub['bg']}>{lb['bg']}", "Background", comp, "Background colour differs (confirm on screen)", ub["bg"], lb["bg"])
        if ub["bgimg"] != lb["bgimg"]:
            add(f"bgimg:{li}:{ub['bgimg']}", "Background", comp, "Background image on one side only (often wrong: confirm on screen)",
                "image" if ub["bgimg"] else "none", "image" if lb["bgimg"] else "none")
        if ub["gap"] is not None and lb["gap"] is not None and abs(ub["gap"] - lb["gap"]) > 2:
            add(f"gap:{li}:{ub['gap']}>{lb['gap']}", "Spacing", comp, "Gap below component differs", f"{ub['gap']}px", f"{lb['gap']}px")
        compare_content(ub, lb, comp, str(li), add)
    # Tabs, accordions and the header are paired across the whole page, not per block:
    # a heading of a different level on one side moves them into another block.
    compare_tab_groups(u, l, add)
    compare_accordions(u, l, add)
    compare_header(u, l, add)


def compare_content(ub, lb, comp, key, add):
    """Text colours, alignment, CTAs, images and text of a block, tab panel or accordion item."""
    uc = sorted({t["color"] for t in ub["texts"]}); lc = sorted({t["color"] for t in lb["texts"]})
    uc_ = [c for c in uc if c not in lc and not any((c, x) in IGNORED_COLOURS for x in lc)]
    lc_ = [c for c in lc if c not in uc and not any((x, c) in IGNORED_COLOURS for x in uc)]
    if uc_ or lc_:
        add(f"textcolor:{key}:{','.join(uc_)}>{','.join(lc_)}", "Colour", comp, "Text colours differ",
            ", ".join(uc_) or "-", ", ".join(lc_) or "-")
    ua = [t["align"] for t in ub["texts"][:3]]; la = [t["align"] for t in lb["texts"][:3]]
    if ua and la and ua[0] != la[0]:
        add(f"textalign:{key}:{ua[0]}>{la[0]}", "Alignment", comp, "Body text alignment differs", ua[0], la[0])
    lctas = {norm(c["text"]): c for c in lb["ctas"]}; uctas = {norm(c["text"]): c for c in ub["ctas"]}
    for k, lcta in lctas.items():
        ucta = uctas.get(k)
        if ucta is None:
            if len(uctas) < len(lctas):
                add(f"ctamissing:{key}", "CTA", comp, f'CTA "{lcta["text"]}" missing on UAT', "-", lcta["text"])
            continue
        style = lambda c: f'{c["color"]} on {c["bg"]} border={c["border"]} r={c["r"]}{" icon" if c["icon"] else ""}{" PLAIN" if c["plain"] else ""}'
        if style(ucta) != style(lcta):
            add(f"ctastyle:{style(ucta)}>{style(lcta)}", "CTA", comp, f'CTA style differs ("{lcta["text"]}")', style(ucta), style(lcta))
        if abs(ucta["h"] - lcta["h"]) > 4:
            add(f"ctah:{key}:{ucta['h']}>{lcta['h']}", "CTA", comp, f'CTA height differs ("{lcta["text"]}")', f'{ucta["h"]}px', f'{lcta["h"]}px')
        if href_key(ucta["href"]) != href_key(lcta["href"]):
            add(f"ctahref:{key}:{href_key(ucta['href'])}>{href_key(lcta['href'])}", "Link", comp,
                f'CTA "{lcta["text"]}" links elsewhere (check final page after redirects)', ucta["href"], lcta["href"])
    broken = [m["file"] for m in ub["imgs"] if m["broken"]]
    if broken:
        add(f"imgbroken:{key}", "Image", comp, "Broken image on UAT", ", ".join(broken), "-")
    if len(ub["imgs"]) != len(lb["imgs"]):
        add(f"imgcount:{key}:{len(ub['imgs'])}>{len(lb['imgs'])}", "Image", comp, "Number of images differs", str(len(ub["imgs"])), str(len(lb["imgs"])))
    else:
        for um, lm in zip(ub["imgs"], lb["imgs"]):
            if lm["w"] and lm["h"] and um["w"] and (um["w"] * um["h"]) / (lm["w"] * lm["h"]) < 0.6:
                add(f"imgsize:{key}:{lm['file']}", "Image", comp, "Image noticeably smaller on UAT",
                    f'{um["file"]} {um["w"]}x{um["h"]}', f'{lm["file"]} {lm["w"]}x{lm["h"]}')
    for a, b in text_changes(ub["txt"], lb["txt"]):
        add(f"text:{key}", "Content", comp, "Text differs", a, b)


def url_lead(u, l):
    """(uat, live) query + hash after a click when they differ; None when equal or not captured."""
    if "url" not in u or "url" not in l or u["url"] == l["url"]:
        return None
    return u["url"] or "(none)", l["url"] or "(none)"


def compare_tab_groups(u, l, add):
    """Pairs each live tab set with the UAT tab set sharing the most titles, anywhere on the page."""
    titles = lambda b: {norm(t.lstrip("*")) for t in b["tabs"]}
    ug = [(i, b) for i, b in enumerate(u["blocks"]) if b.get("tabs")]
    lg = [(i, b) for i, b in enumerate(l["blocks"]) if b.get("tabs")]
    used = set()
    for li, lb in lg:
        comp = f'{lb["head"][:60]} (live #{li})'
        best = max([(len(titles(lb) & titles(ub)), ui) for ui, ub in ug if ui not in used], default=(0, None))
        if best[1] is None or (best[0] == 0 and not len(ug) == len(lg) == 1):
            add(f"tabsmissing:{li}", "Missing component", comp, "Tabs on live, not on UAT", "-", " / ".join(lb["tabs"]))
            continue
        used.add(best[1])
        ub = u["blocks"][best[1]]
        if [t.lstrip("*") for t in ub["tabs"]] != [t.lstrip("*") for t in lb["tabs"]]:
            add(f"tabs:{li}", "Tabs", comp, "Tab titles differ", " / ".join(ub["tabs"]), " / ".join(lb["tabs"]))
        elif ub["tabs"] != lb["tabs"]:
            add(f"tabactive:{li}", "Default state", comp, "Different tab active on load", " / ".join(ub["tabs"]), " / ".join(lb["tabs"]))
        compare_tabs(ub, lb, li, add)
    for ui, ub in ug:
        if ui not in used:
            add(f"tabsextra:{ui}", "Extra component", f'{ub["head"][:60]} (UAT #{ui})', "Tabs on UAT, not on live", " / ".join(ub["tabs"]), "-")


def compare_tabs(ub, lb, li, add):
    """Content of each tab after clicking it. Tabs pair by position when both sides have
    the same number (titles may differ: that is its own lead), else by title."""
    ut, lt = ub.get("tabPanels") or [], lb.get("tabPanels") or []
    if not ut or not lt:
        return
    pairs = list(zip(ut, lt)) if len(ut) == len(lt) else \
        [(next((u for u in ut if norm(u["tab"]) == norm(l["tab"])), None), l) for l in lt]
    for n, (u, l) in enumerate(pairs):
        if u is None or u.get("skipped") or l.get("skipped"):
            continue
        comp = f'{lb["head"][:40]} › tab "{l["tab"]}" (live #{li})'
        if url_lead(u, l):
            add(f"taburl:{li}:{n}", "Tabs", comp, "URL query/hash after clicking the tab differs", *url_lead(u, l))
        if u.get("selected") is False and l.get("selected") is not False:
            add(f"tabclick:{li}:{n}", "Tabs", comp, "Tab does not switch when clicked on UAT", f'"{u["tab"]}" stays unselected', "switches")
            continue
        compare_content(u, l, comp, f"{li}:tab:{n}", add)


def compare_accordions(u, l, add):
    """Every accordion item on the page, expanded: pairs items by title (position when titles all differ)."""
    ui = [(i, b["head"], it) for i, b in enumerate(u["blocks"]) for it in b.get("accItems") or []]
    la = [(i, b["head"], it) for i, b in enumerate(l["blocks"]) for it in b.get("accItems") or []]
    if not ui and not la:
        return
    by_title = {norm(it["title"]): it for _, _, it in ui}
    matched = sum(norm(it["title"]) in by_title for _, _, it in la)
    pairs = [(x[2], y) for x, y in zip(ui, la)] if not matched and len(ui) == len(la) else \
        [(by_title.get(norm(y[2]["title"])), y) for y in la]
    for n, (uit, (li, head, lit)) in enumerate(pairs):
        comp = f'{head[:40]} › accordion "{lit["title"][:40]}" (live #{li})'
        if uit is None:
            add(f"accmissing:{li}:{n}", "Missing component", comp, "Accordion item on live, not on UAT", "-", lit["title"])
            continue
        if uit["open"] != lit["open"]:
            add(f"accopen:{li}:{n}", "Default state", comp, "Accordion item open on load differs",
                "open" if uit["open"] else "closed", "open" if lit["open"] else "closed")
        if uit.get("skipped") or lit.get("skipped"):
            continue
        if uit.get("opened") is False and lit.get("opened") is not False:
            add(f"accclick:{li}:{n}", "Accordion", comp, "Accordion item does not expand when clicked on UAT", "stays closed", "expands")
            continue
        if url_lead(uit, lit):
            add(f"accurl:{li}:{n}", "Accordion", comp, "URL query/hash after expanding the item differs", *url_lead(uit, lit))
        compare_content(uit, lit, comp, f"{li}:acc:{n}", add)
    if matched or not la:
        live_titles = {norm(it["title"]) for _, _, it in la}
        for n, (i, head, it) in enumerate(ui):
            if norm(it["title"]) not in live_titles:
                add(f"accextra:{i}:{n}", "Extra component", f'{head[:40]} › accordion "{it["title"][:40]}" (UAT #{i})',
                    "Accordion item on UAT, not on live", it["title"], "-")


def compare_header(u, l, add):
    """Top-right header links and buttons (the rest of the header is excluded)."""
    if "headerCtas" not in u or "headerCtas" not in l:
        return
    kind = lambda c: "Header link" if c["plain"] else "Header CTA"
    # A plain link's corner radius can't be seen: compare its colour only.
    style = lambda c: c["color"] if c["plain"] else f'{c["color"]} on {c["bg"]} border={c["border"]} r={c["r"]}'
    uh = {norm(c["text"]): c for c in u["headerCtas"]}
    lh = {norm(c["text"]): c for c in l["headerCtas"]}
    comp = "Header (top right)"
    for n, (k, lc) in enumerate(lh.items()):
        uc = uh.get(k)
        if uc is None:
            add(f"hdrmissing:{kind(lc)}:{n}", kind(lc), comp, f'{kind(lc)} "{lc["text"]}" missing on UAT', "-",
                f'{lc["text"]} ({style(lc)}) -> {lc["href"] or "-"}')
            continue
        if style(uc) != style(lc) and not (uc["plain"] and lc["plain"] and (uc["color"], lc["color"]) in IGNORED_HEADER_COLOURS):
            add(f"hdrstyle:{style(uc)}>{style(lc)}", kind(lc), comp, f'{kind(lc)} style differs ("{lc["text"]}")', style(uc), style(lc))
        if href_key(uc["href"]) != href_key(lc["href"]):
            add(f"hdrhref:{n}:{href_key(uc['href'])}>{href_key(lc['href'])}", "Link", comp,
                f'{kind(lc)} "{lc["text"]}" links elsewhere (check final page after redirects)', uc["href"], lc["href"])
    for n, (k, uc) in enumerate(uh.items()):
        if k not in lh and k not in EXPECTED_HEADER_EXTRA:
            add(f"hdrextra:{kind(uc)}:{n}", kind(uc), comp, f'{kind(uc)} "{uc["text"]}" on UAT, not on live',
                f'{uc["text"]} ({style(uc)}) -> {uc["href"] or "-"}', "-")
    # Navigation menu rows: labels and order only (mega menus are not opened).
    un, ln = u.get("headerNav") or [], l.get("headerNav") or []
    for i in range(max(len(un), len(ln))):
        ur = un[i] if i < len(un) else {"row": ln[i]["row"], "items": []}
        lr = ln[i] if i < len(ln) else {"row": ur["row"], "items": []}
        ui, li = [norm(x) for x in ur["items"]], [norm(x) for x in lr["items"]]
        if ui == li:
            continue
        rowc = f'Header navigation ({lr["row"]})'
        missing = [x for x, k in zip(lr["items"], li) if k not in ui]
        extra = [x for x, k in zip(ur["items"], ui) if k not in li]
        if missing or extra:
            add(f"hdrnav:{i}:items", "Header navigation", rowc, "Menu items differ (labels or items missing / extra)",
                " | ".join(ur["items"]) or "-", " | ".join(lr["items"]) or "-")
        elif ui != li:
            add(f"hdrnav:{i}:order", "Header navigation", rowc, "Menu items in a different order",
                " | ".join(ur["items"]), " | ".join(lr["items"]))


def page_status(d, err):
    if err:
        return err
    if not d:
        return "Not captured"
    if d.get("status") == 404 or d.get("is404"):
        return "404"
    if not d["blocks"]:
        return "Empty"
    return "Loads"


def run(work):
    work = Path(work)
    plan = json.loads((work / "plan.json").read_text(encoding="utf-8-sig"))
    errors = plan.get("errors", {})
    snap = {}
    for f in work.glob("*-*.json"):
        if f.stem.endswith(("-uat", "-live")):
            snap[f.stem] = json.loads(f.read_text(encoding="utf-8-sig"))
    leads, coverage = {}, []

    def adder(code):
        def add(sig, kind, comp, summary, uat, live):
            g = leads.setdefault(sig, {"sig": sig, "kind": kind, "component": comp, "summary": summary, "locales": []})
            for x in g["locales"]:
                if x["locale"] == code and (x["uat"], x["live"]) == (uat, live):
                    x["count"] = x.get("count", 1) + 1  # e.g. several CTAs with the same fault
                    return
            g["locales"].append({"locale": code, "uat": uat, "live": live})
        return add

    en_u, en_l = snap.get("en-uat"), snap.get("en-live")
    for code in plan["locales"]:
        c = code.lower(); u, l = snap.get(f"{c}-uat"), snap.get(f"{c}-live")
        urls = plan["locales"][code]
        us, ls = page_status(u, errors.get(f"{c}-uat")), page_status(l, errors.get(f"{c}-live"))
        lang = "Yes"
        add = adder(code)
        if u and l:
            if u["lang"].split("-")[0].lower() != l["lang"].split("-")[0].lower():
                lang = f'UAT lang={u["lang"]}, live lang={l["lang"]}'
            if code in NON_LATIN:
                pat = NON_LATIN[code]
                ur, lr = len(re.findall(pat, page_text(u))), len(re.findall(pat, page_text(l)))
                if lr > 50 and ur < lr * 0.2:
                    lang = "UAT content is not translated"
                elif ur > 50 and lr < ur * 0.2:
                    lang = "Live content is not translated"
            elif code != "EN" and en_u and en_l:
                if sim(page_text(u), page_text(en_u)) > 0.8 and sim(page_text(l), page_text(en_l)) < 0.5:
                    lang = "UAT shows English"
                elif sim(page_text(l), page_text(en_l)) > 0.8 and sim(page_text(u), page_text(en_u)) < 0.5:
                    lang = "Live shows English"
            if lang != "Yes":
                add(f"lang:{lang}", "Locale", "Whole page", lang, u["lang"], l["lang"])
            if u["forms"] != l["forms"]:
                add(f"forms:{u['forms']}>{l['forms']}", "Missing component", "Forms", "Number of forms differs", str(u["forms"]), str(l["forms"]))
            ufin, lfin = urlparse(u["url"]).path, urlparse(l["url"]).path
            if ufin.rstrip("/") != urlparse(urls["uat"]).path.rstrip("/") or lfin.rstrip("/") != urlparse(urls["live"]).path.rstrip("/"):
                if not (code == "RU" and "/ru-cis/" in lfin):
                    us = us if ufin.rstrip("/") == urlparse(urls["uat"]).path.rstrip("/") else f"Redirects to {u['url']}"
                    ls = ls if lfin.rstrip("/") == urlparse(urls["live"]).path.rstrip("/") else f"Redirects to {l['url']}"
            compare_locale(code, u, l, add)
        if us != ls and not (us == "Loads" and ls.startswith("Redirects to") and code == "RU"):
            add(f"status:{us[:12]}>{ls[:12]}", "Locale", "Whole page", "Page status differs", us, ls)
        coverage.append({"locale": code, "language": NAMES[code], "uat": urls["uat"], "live": urls["live"],
                         "listed_on_live": urls.get("listed", True), "uat_status": us, "live_status": ls, "lang_ok": lang,
                         "blocks": f'{len(u["blocks"]) if u else "-"}/{len(l["blocks"]) if l else "-"}'})

    for g in leads.values():
        g["locale_codes"] = list(dict.fromkeys(x["locale"] for x in g["locales"]))
    grouped = sorted(leads.values(), key=lambda g: (-len(g["locale_codes"]), g["kind"]))
    for n, g in enumerate(grouped, 1):
        g["id"] = f"L{n}"
    (work / "diff.json").write_text(json.dumps({"coverage": coverage, "leads": grouped}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# Leads: {plan['slug']}", "", f"UAT {plan['uat']}  |  Live {plan['live']}", "",
          "## Coverage", "", "| Locale | UAT | Live | Lang OK | Blocks U/L | Listed on live |", "|---|---|---|---|---|---|"]
    md += [f"| {c['locale']} | {c['uat_status']} | {c['live_status']} | {c['lang_ok']} | {c['blocks']} | {'yes' if c['listed_on_live'] else 'NO'} |" for c in coverage]
    md += ["", f"## Leads ({len(grouped)}, grouped: same values in several locales = one lead)", ""]
    for g in grouped:
        locs, codes = g["locales"], g["locale_codes"]
        same = len({(x["uat"], x["live"]) for x in locs}) == 1
        times = max(x.get("count", 1) for x in locs)
        md.append(f"- **{g['id']} [{g['kind']}] {g['component']}**: {g['summary']}{f' (×{times} on the page)' if times > 1 else ''}"
                  f" — {len(codes)} locale{'s' if len(codes) > 1 else ''}: {', '.join(codes)}")
        for x in (locs[:1] if same else locs[:8]):
            md.append(f"  - {'' if same else x['locale'] + ': '}UAT `{x['uat']}` | live `{x['live']}`")
        if not same and len(locs) > 8:
            md.append(f"  - … {len(locs) - 8} more in diff.json")
    (work / "diff.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return len(grouped)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"{run(sys.argv[1])} leads -> {Path(sys.argv[1]) / 'diff.md'}")
