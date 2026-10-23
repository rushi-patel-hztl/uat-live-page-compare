# Shared by build.py and recheck.py: locales, page labels, shared-fix groups, severity rules.
LOC = [["EN","English"],["DE","German"],["FR","French"],["ES","Spanish"],["JA","Japanese"],["PT","Portuguese"],["CN","Chinese (Simplified)"],["HU","Hungarian"],["IT","Italian"],["KO","Korean"],["NL","Dutch"],["PL","Polish"],["TH","Thai"],["RU","Russian"],["CS","Czech"],["TW","Chinese (Traditional)"],["TR","Turkish"]]
N2C = {n: c for c, n in LOC}
LABEL = {"special-request-callback":"Request callback","special-reset-management":"Reset management","special-sales-upgrade-request":"Sales upgrade request","special-security-explained":"Security explained","special-splashtop-alternative":"Splashtop alternative","special-teamviewer-alternative":"TeamViewer alternative","special-teamviewer-dex-vs-controlup":"DEX vs ControlUp","special-teamviewer-dex-vs-lakeside":"DEX vs Lakeside","special-teamviewer-dex-vs-nexthink":"DEX vs Nexthink"}
GROUPS = {  # signature -> group key
 **{s:"loc404" for s in ["locale-404","locale-live-404","locale-404-live","locale-status-404"]},
 **{s:"eyebrow" for s in ["eyebrow-missing","hero-eyebrow","hero-eyebrow-bg"]},
 **{s:"table" for s in ["table-broken-icons","table-broken-images"]},
 **{s:"faq" for s in ["faq-hash","faq-url-hash","accordion-deeplink"]},
 "de-duplicated-blocks":"dedup","header-nav-labels":"nav","cta-banner-theme":"banner","faq-extra-locales":"faqextra",
 "hero-image-corners":"heroimg","hero-image-differs":"heroimg","hero-style":"heroimg",
}
GT = {"loc404":("Live returns 404 while UAT loads the page","Source 404"),
 "eyebrow":("Eyebrow label above the heading is missing on UAT","Content"),
 "table":("Comparison table check/cross icons are broken images on UAT","Image"),
 "faq":("Expanding an accordion / FAQ item sets no URL hash on UAT (live deep-links)","Accordion"),
 "dedup":("German UAT repeats the page blocks many times","Duplicated component"),
 "nav":("Menu labels differ from live in DE and ES","Header"),
 "banner":("CTA banner is bright blue with white text on UAT; live is light with navy text","Colour"),
 "faqextra":("FAQ exists on UAT in locales where live is 404","Extra component"),
 "heroimg":("Hero image differs from live (corners, size or asset)","Image")}
FIX = {"loc404":("Content / config","Locale versions are missing or unpublished on one side. Create or publish the language versions in the CMS, or confirm that live is meant to return 404."),
 "eyebrow":("Component","The eyebrow field is not rendered on UAT. Check the rendering variant of the hero / text component and that the datasource field was migrated."),
 "table":("Content / media","Comparison-table check and cross icons point to media that is missing on UAT. Re-link or publish the media items."),
 "faq":("Component","The shared accordion does not write the opened item to the URL hash. Fix it once in the accordion component."),
 "dedup":("Template","German pages render the same blocks several times. Check the DE layout, placeholder settings and datasource inheritance."),
 "nav":("Content","Main menu labels differ in DE and ES. Update the menu item translations or dictionary entries."),
 "banner":("Component","The CTA banner theme variant differs (bright blue with white text on UAT). Set the light theme in the shared CTA banner component."),
 "faqextra":("Config","The FAQ shows on UAT in locales that live does not publish. Resolves together with the locale 404s."),
 "heroimg":("Component","Hero image corners, size or asset differ. Check the hero component styling and its media item.")}
BLOCKER_KINDS = {"Source 404","Target 404","Locale","Duplicated component","Missing component"}
MAJOR_KINDS = {"Content","Extra component","URL","Accordion","Header","CTA"}
MINOR_SIGS = {"awards-heading-typo","award-heading","hero-eyebrow","hero-eyebrow-bg"}
def severity(kind, sig):
    if kind in BLOCKER_KINDS: return "Blocker"
    if sig in MINOR_SIGS: return "Minor"
    if kind in MAJOR_KINDS or (sig or "").startswith("table-") or sig=="hero-image-differs": return "Major"
    return "Minor"
