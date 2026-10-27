# Tracker rules, shared by build.py, upgrade.py and recheck.py: locales, page labels, shared-fix groups, severity rules.
LOC = [["EN","English"],["DE","German"],["FR","French"],["ES","Spanish"],["JA","Japanese"],["PT","Portuguese"],["CN","Chinese (Simplified)"],["HU","Hungarian"],["IT","Italian"],["KO","Korean"],["NL","Dutch"],["PL","Polish"],["TH","Thai"],["RU","Russian"],["CS","Czech"],["TW","Chinese (Traditional)"],["TR","Turkish"]]
N2C = {n: c for c, n in LOC}
LABEL = {"special-request-callback":"Request callback","special-reset-management":"Reset management","special-sales-upgrade-request":"Sales upgrade request","special-security-explained":"Security explained","special-splashtop-alternative":"Splashtop alternative","special-teamviewer-alternative":"TeamViewer alternative","special-teamviewer-dex-vs-controlup":"DEX vs ControlUp","special-teamviewer-dex-vs-lakeside":"DEX vs Lakeside","special-teamviewer-dex-vs-nexthink":"DEX vs Nexthink"}
GROUPS = {  # signature -> group key
 **{s:"enfallback" for s in ["locale-en-fallback","locale-english-content","locale-live-english"]},
 **{s:"loc404" for s in ["locale-404","locale-live-404","locale-404-live","locale-status-404"]},
 **{s:"eyebrow" for s in ["eyebrow-missing","hero-eyebrow","hero-eyebrow-bg"]},
 **{s:"table" for s in ["table-broken-icons","table-broken-images"]},
 **{s:"faq" for s in ["faq-hash","faq-url-hash","accordion-deeplink"]},
 "de-duplicated-blocks":"dedup","header-nav-labels":"nav","cta-banner-theme":"banner","faq-extra-locales":"faqextra",
 "hero-image-corners":"heroimg","hero-image-differs":"heroimg","hero-style":"heroimg",
}
GT = {"enfallback":("Live serves English content in a localised URL","EN Fallback"),
 "loc404":("Live returns 404 while UAT loads the page","Source 404"),
 "eyebrow":("Eyebrow label above the heading is missing on UAT","Content"),
 "table":("Comparison table check/cross icons are broken images on UAT","Image"),
 "faq":("Expanding an accordion / FAQ item sets no URL hash on UAT (live deep-links)","Accordion"),
 "dedup":("German UAT repeats the page blocks many times","Duplicated component"),
 "nav":("Menu labels differ from live in DE and ES","Header"),
 "banner":("CTA banner is bright blue with white text on UAT; live is light with navy text","Colour"),
 "faqextra":("FAQ exists on UAT in locales where live is 404","Extra component"),
 "heroimg":("Hero image differs from live (corners, size or asset)","Image")}
FIX = {"enfallback":("Content","Live returns 200 but the whole page is in English, so the locale is falling back to EN. Translate the page in Sitecore, or confirm live should stay English there and align UAT."),
 "loc404":("Content / config","Source 404 (live 404, UAT loads): unpublish the page in these locales in Sitecore, or confirm live should have it. Target 404 (UAT 404, live loads): create and publish the missing language version."),
 "eyebrow":("Component","The eyebrow field is not rendered on UAT. Check the rendering variant of the hero / text component and that the datasource field was migrated."),
 "table":("Content / media","Comparison-table check and cross icons point to media that is missing on UAT. Re-link or publish the media items."),
 "faq":("Component","The shared accordion does not write the opened item to the URL hash. Fix it once in the accordion component."),
 "dedup":("Template","German pages render the same blocks several times. Check the DE layout, placeholder settings and datasource inheritance."),
 "nav":("Content","Main menu labels differ in DE and ES. Update the menu item translations or dictionary entries."),
 "banner":("Component","The CTA banner theme variant differs (bright blue with white text on UAT). Set the light theme in the shared CTA banner component."),
 "faqextra":("Config","The FAQ shows on UAT in locales that live does not publish. Unpublishing those locales in Sitecore clears it."),
 "heroimg":("Component","Hero image corners, size or asset differ. Check the hero component styling and its media item.")}
BLOCKER_KINDS = {"Target 404","Locale","Duplicated component","Component Missing"}
MAJOR_KINDS = {"Header navigation","Accordion URL","Tabs URL","Form","EN Fallback","Content Missing","Additional Component","Content","Extra component","URL","Accordion","Header","CTA"}
MINOR_SIGS = {"faq-extra-locales","awards-heading-typo","award-heading","hero-eyebrow","hero-eyebrow-bg"}
UI_KINDS = {"UI","Colour","Background","Alignment","Layout","Spacing / heading","Layout / spacing","Image / colour / spacing","Accordion style"}
UI_SIGS = {"cards-icon-size","awards-badge-size","cta-explore-style","hero-image-corners","hero-text-image-gap"}
UI_WORDS = ("colour","color","spacing","layout","align","background","style")
def is_ui(kind, sig): return kind in UI_KINDS or sig in UI_SIGS or kind == "UI" or any(w in kind.lower() for w in UI_WORDS)
import re
TYPE_ORDER = ["Source 404","Target 404","EN Fallback","Content Missing","Component Missing","Additional Component","Duplicated Component","Header","Missing Image","UI","Font Colour","Font Size","Other"]
# Font Size: the size of text differs by more than 2px (e.g. 16px vs 20px). Only tags issues already reported;
# the compare skill's own rules on font size are unchanged. Other styling in the same issue keeps UI as well.
FONT_SIZE_RX = re.compile(r"\bfont[- ]sizes?\b|\b(text|font|type|heading|title|label|copy|eyebrow|subtitle|subheading)s?\b[^.;]{0,30}\b(size[sd]?|smaller|larger|bigger)\b"
                          r"|\b(smaller|larger|bigger)\b[^.;]{0,15}\b(text|font|heading|title|label)s?\b", re.I)
PX_RX = re.compile(r"(\d+(?:\.\d+)?)\s*px", re.I)
def font_size_over_2px(*texts):
    """True unless the issue's px values show a difference of 2px or less (no values: trust the wording)."""
    px = [float(v) for s in texts for v in PX_RX.findall(s or "")]
    return len(px) < 2 or max(px) - min(px) > 2
# Font Colour: the colour of text (titles, headings, labels, links, body copy). An issue that also changes
# background, border, spacing, alignment, size or layout keeps UI as well.
FONT_RX = re.compile(r"\b(text|title|heading|label|link|subtitle|subheading|eyebrow|copy|font)s?\b[^.;]{0,50}\b(colou?rs?|navy|grey|gray|blue|black|white|near-black)\b"
                     r"|\bcolou?rs?\b[^.;]{0,25}\b(text|title|heading|label|link|font)s?\b", re.I)
NON_FONT_UI_RX = re.compile(r"\b(background|bg|border|fill(ed)?|spacing|gap|align(ed|ment)?|centred|centered|layout|radius|corners?|size|divider|line|rule|outline|shadow|width|height|theme|banner|strip)\b", re.I)
IMG_RX = re.compile(r"((image|icon|logo|badge|thumbnail|picture|photo)s?[^.;]{0,45}(missing|broken|not (load|shown|displayed|render)|absent|no longer|without)|(missing|broken|absent)[^.;]{0,35}(image|icon|logo|badge|thumbnail)s?|no (check |cross )?(image|icon)s?)", re.I)
# Text link styling (colour, underline, weight, e.g. live blue vs UAT black): always UI and Major.
# Matched on the compare skill's linkcolor/linkstyle leads, or on the wording.
LINK_RX = re.compile(r"\blinks?\b[^.;]{0,30}\b(colou?rs?|underlined?|underlines|bold|weight|blue|black|navy|grey|gray|white)\b|\b(colou?rs?|underline)\b[^.;]{0,25}\blinks?\b", re.I)
def is_link_style(sig, text=""): return (sig or "").startswith(("linkcolor", "linkstyle")) or bool(LINK_RX.search((text or "").split(" | ")[0]))
def is_header(kind, component, sig): return kind.lower().startswith("header") or component.lower().startswith("header") or (sig or "").lower().startswith("header")
def types_of(kind, ui, text, component="", sig="", live=""):
    """Filterable issue types: the meaningful ones only; an issue can carry several."""
    t = []
    if kind in ("Source 404","Target 404","EN Fallback","Content Missing","Component Missing","Additional Component"): t.append(kind)
    if kind == "Duplicated component": t.append("Duplicated Component")
    if is_header(kind, component, sig): t.append("Header")
    sentence = text.split(" | ")[0]
    if is_link_style(sig, sentence):
        t.append("UI")
        if IMG_RX.search(text): t.append("Missing Image")
        return t
    fsize = bool(FONT_SIZE_RX.search(sentence)) and font_size_over_2px(text, live)
    if ui or fsize:
        rest = FONT_SIZE_RX.sub(" ", sentence) if fsize else sentence
        colour = ui and FONT_RX.search(sentence)
        if ui and ((not colour and not fsize) or NON_FONT_UI_RX.search(rest)): t.append("UI")
        if colour: t.append("Font Colour")
        if fsize: t.append("Font Size")
    if IMG_RX.search(text): t.append("Missing Image")
    return t or ["Other"]
def severity(kind, sig, text=""):
    if kind == "Source 404": return "Minor"  # live 404, UAT loads: unpublish the page in Sitecore
    if kind in BLOCKER_KINDS: return "Blocker"
    if is_link_style(sig, text): return "Major"
    if sig in MINOR_SIGS: return "Minor"
    if kind in MAJOR_KINDS or (sig or "").startswith("table-") or sig=="hero-image-differs": return "Major"
    return "Minor"


# ---- shared by build.py and upgrade.py ----
KIND_MAP = {"Missing component":"Component Missing","Extra component":"Additional Component"}
MISSING_RX = re.compile(r"(?<![a-z])(missing|absent|empty|not (shown|rendered|present|displayed)|no (text|heading|subheading|eyebrow|image|caption|description))(?![a-z])", re.I)
GROUPS_EN = {s for s, g in GROUPS.items() if g == "enfallback"}
def norm_kind(i):
    """Map a raw finding to its tracker kind (Source 404, EN Fallback, Content Missing, ...)."""
    kind, sig = i["kind"], i.get("signature") or i.get("group") or ""
    if kind == "Locale" and re.match(r"^(live )?404", i["live"].strip(), re.I): return "Source 404"
    if kind == "Locale" and i["uat"].strip().startswith("404"): return "Target 404"
    if sig in GROUPS_EN or (kind == "Locale" and re.search(r"live (shows|loads|serves|returns)[^.]*english", (i["issue"] + " " + i["live"]).lower())): return "EN Fallback"
    if kind in KIND_MAP: return KIND_MAP[kind]
    if kind.startswith("Content") and MISSING_RX.search(i["issue"]): return "Content Missing"
    return kind
def comp_key(c): return " ".join(re.sub(r"[^a-z0-9 ]", " ", c.split("(")[0].lower()).split()[:2])
def messy_check(issues, secs, version_mismatch=False):
    """Messy = version mismatch, 2+ missing/duplicated components or a blank/repeating locale, or >=50% of sections with a Blocker/Major issue (4+ sections)."""
    cur = [i for i in issues if not i["rc"] == "fixed"]; why = []; hit = []
    if version_mismatch or any(i["sig"] == "version-mismatch" for i in cur):
        why.append("UAT and live are different versions of the page"); hit += [i for i in cur if i["sig"] == "version-mismatch"]
    md = [i for i in cur if i["kind"] in ("Component Missing", "Duplicated component")]
    if len(md) >= 2: why.append(f"{len(md)} components are missing or duplicated"); hit += md
    bl = [i for i in cur if i["group"] == "dedup" or "dedup" in i["sig"] or "duplicated" in i["sig"] or re.match(r"^locale-.*-(empty|blank)$", i["sig"])
          or (i["kind"] == "Locale" and re.search(r"(renders no content|page is empty|is empty|0 blocks|repeats)", (i["issue"] + " " + i["uat"]).lower()))]
    hit += bl
    if bl: why.append("A locale loads blank or repeats page blocks (" + ", ".join(sorted({l for i in bl for l in i["langs"]})) + ")")
    aff = len({comp_key(i["component"]) for i in cur if i["sev"] in ("Blocker", "Major") and i["kind"] not in ("Locale", "Header", "Header navigation") and not i["component"].lower().startswith("whole page")})
    aff = min(aff, secs)
    if secs >= 4 and aff * 2 >= secs:
        why.append(f"{aff} of {secs} sections have a Blocker or Major issue")
        hit += [i for i in cur if i["sev"] in ("Blocker", "Major") and i["kind"] not in ("Locale", "Header", "Header navigation") and not i["component"].lower().startswith("whole page")]
    for i in hit: i["messy"] = True
    return dict(on=bool(why), why=why, sections=secs, affected=aff)
FIX_BY_TYPE = {
 "Source 404": ("Content / config", "Live returns 404 but UAT loads the page. Unpublish it in these locales in Sitecore, or confirm live should have it."),
 "Target 404": ("Content / config", "UAT returns 404 but live loads the page. Create and publish the missing language version."),
 "EN Fallback": ("Content", "Live serves English in a localised URL. Translate the page in Sitecore, or confirm live should stay English and align UAT."),
 "Content Missing": ("Content", "A field inside the component is empty or not migrated. Fill it in Sitecore or re-push the component data."),
 "Component Missing": ("Template / content", "The component is not on the UAT page. Add it to the page or re-push the presentation details."),
 "Additional Component": ("Template / content", "UAT has a component that live does not. Remove it or confirm it is intended."),
 "Duplicated Component": ("Template", "Blocks render more than once. Check the layout, placeholder settings and datasource inheritance."),
 "Missing Image": ("Content / media", "A media item is missing or not published. Re-link or publish it."),
 "Header": ("Content / config", "Header menu labels, order or the header CTA differ. Update the menu item titles and the header CTA in the shared header settings."),
 "UI": ("Component", "Styling or layout differs in a shared component. Fix it once in the component styles."),
 "Font Colour": ("Component", "Text colour differs from live. Fix the colour token or text style in the shared component."),
 "Font Size": ("Component", "Text size differs from live by more than 2px. Fix the type scale or text style in the shared component."),
 "Other": ("Component / content", "Check the components and content listed on each page."),
}
