# Worker: analyse captured pages

You turn one captured page's machine leads into confirmed, grouped findings,
and a report (no Confluence: results go to the QA tracker artifact the
orchestrator builds at the end). Work fast but report nothing you have not
confirmed. Run commands from the project folder with `py -3.13`; `S/` is
the absolute path of the skill's `scripts/` folder (given in your prompt;
it sits beside the folder holding this file). Never use Claude in Chrome,
never type a password, never touch another page's files.
Never write to Confluence.

Repeat for up to 3 pages (or the number in your prompt):

## 1. Claim a page

`py -3.13 S/batch.py next 1` prints a slug, or `(none captured yet)`: then
stop and return what you have.

## 2. Read the evidence

1. `work/<slug>/diff.md`: the coverage table (status and language per
   locale) and the leads, already grouped across locales and already
   filtered for the standing exclusions. Leads are candidates, not findings.
2. The EN slices `work/<slug>/en-uat-NN.jpg` and `en-live-NN.jpg`: look at
   both pages top to bottom. This catches what the snapshot can't (layout
   flipped, image cropped or missing, icons, squeezed CTAs, extra dividers).
   Add anything you see as a candidate.
3. When a lead needs detail, read the snapshot lines in
   `work/<slug>/<code>-uat.txt` / `<code>-live.txt` (`#n` sections with
   `T` text, `CTA`, `IMG`, `TABS`, `ACC`, `TXT` lines). Capture clicks every
   tab and expands every accordion item: each one has a `TAB "<title>"` or
   `ACCI "<title>"` line followed by its own `· T / CTA / IMG / TXT` lines,
   so search those too when looking for content.

## 3. Decide each lead

- **Drop** leads that are noise: carousel/slider controls ("Go to slide 2"),
  rotating testimonials or logos, text that only moved, heading-pairing
  mix-ups (one extra block shifting the pairs), near-identical colours
  that are the accepted #2D2D2D/#545454 body text, body text #2D2D2D (UAT)
  vs navy #050A52 (live), heading/card-title #050A52 (UAT) vs #141414
  (live), accordion/FAQ titles #050A52 (UAT) vs #141414 or #000000 (live),
  the expected header CTA design (UAT outlined navy r=8 vs live white with a
  #3056EF border r=4), tab label colours (UAT active #3056EF / inactive
  #27272A vs live navy / grey), no divider above the first accordion row, a heading level that differs on its own (H5 vs H3), and anything under the
  ground rules below.
- **`bgimg` and `bg` leads, and block heights, are often wrong**: confirm on
  screen before keeping them.
- **Link leads**: keep only if the two hrefs end on different pages. Check
  with `browse.py` and a `js` of `location.href` after loading, or by
  loading both URLs, if unsure.
- **Missing/extra component**: before keeping, search the other side's
  snapshot `TXT` lines for the heading/text (it may sit in a tab or under a
  different heading).
- **Tab and accordion leads** (component `… › tab "<title>"` or
  `… › accordion "<title>"`) compare the content shown after clicking that
  tab or expanding that item. "Does not switch / does not expand when clicked
  on UAT" is a real issue if confirmed on screen. Lines marked `(not clicked:
  …)`, `(not opened: …)` or `(no panel found: whole block)` were not fully
  checked: confirm on screen or list under "Couldn't check".
  Tabs and accordion items are paired across the whole page, so a heading of
  a different level on one side doesn't stop them being compared.
- **URL leads** ("URL query/hash set after clicking the tab / expanding the
  item on one side only"): `url=` on each `TAB` / `ACCI` line is
  `location.search + location.hash` right after the click. Test presence
  only: live setting a query or hash (e.g. `?tab=remote-support`, `#faq-2`)
  and UAT setting none (or the reverse) is an issue if confirmed by clicking
  on both sides (`browse.py` with a `js` of `location.search +
  location.hash`). Both sides setting one with **different values** is
  expected, never an issue (e.g. `#how-quickly-to-see-value` vs
  `#qalist-…-item-…`).
- **Header leads**: pages are captured at 1440px so the full header shows.
  Two things are in scope:
  - `HEADER NAV <row>: a | b | c` lines (component "Header navigation"):
    the items of each menu row, left to right. Report items missing or
    extra on one side, labels that differ (e.g. raw page slugs like
    `world-class-privacy` instead of live's "Data protection"), and a
    different order. One row with all its differences = one issue, listing
    both sides' items. Mega menus are not opened and menu links are not
    followed.
  - `HEADER CTA` lines (component "Header (top right)"): the styled header
    button. Report it missing on one side, a different style or text, or a
    different final destination after redirects (load both hrefs), and
    new-tab behaviour. `HEADER (no CTA in the header)` when there is none.
  The top-bar utility links (contact sales, phone, sign in) are not
  captured and never reported.
- **Status first** (SKILL.md "Status rules"): both sides 404, or both 301/302,
  is expected behaviour, not an issue. Only one side 404 or only one side
  301/302 is an issue with no comparison for that locale (give the
  redirect destination). Internal loads but live redirects elsewhere: don't
  validate, only report where live goes. Both sides redirecting is only
  expected when both end on the same working page: if UAT's redirect ends on
  a 404 or another page, that's an issue (give the whole chain). A capture
  `ERR_HTTP_RESPONSE_CODE_FAILURE` means the page answered 404, not a capture
  fault. Drop every other lead for those locales.
- **Locale leads** (status differs, wrong language, unlisted locale) are
  always issues if real.
- **Dropdowns, videos, anchor links, CTA redirection**: the capture does not
  record these, so check them yourself on both sides for every compared
  locale with `browse.py` and a `js` expression. Examples:
  `[...document.querySelectorAll('a[href^="#"],a[href*="#"]')].map(a=>[a.innerText.trim(),a.getAttribute('href'),!!document.getElementById(decodeURIComponent(a.hash.slice(1)))])`
  for anchors; `[...document.querySelectorAll('video,iframe[src*=youtube],iframe[src*=vimeo],[class*=video] [data-video-id],[data-video-id]')].map(v=>v.currentSrc||v.src||v.dataset.videoId)`
  for videos; `[...document.querySelectorAll('select')].map(s=>[...s.options].map(o=>o.text))`
  for native dropdowns (open custom ones on screen); and for CTAs, the
  `href` + `target` of each, then load both hrefs and compare the final
  `location.href`. See `issue-checklist.md` sections 13-16.
  Anchor links: use live's anchors in the same locale as the reference; do
  not check landing position or sticky-header offset.
- Merge leads with one root cause into one issue (e.g. heading colour + text
  colour of the same hero after a theme swap = one "Hero theme" issue; all
  CTAs with the same wrong style = one issue).
- For each issue, its **languages** are every locale where the confirmed
  lead appears (diff.md lists them). If you confirm only a sample, say so in
  the issue's Live/UAT text, not by dropping languages.

## 4. Annotated screenshots (also your on-screen confirmation)

One UAT + live pair per issue, in one representative language (English if
affected, else the first listed). Write `work/<slug>/shots.json`:

```json
{"out": "reports/screenshots/<slug>", "width": 1440,
 "shots": [{"name": "3-german", "uat": "<UAT URL of that locale>", "live": "<live URL>",
            "anchor": "component heading or text, in that language",
            "mark": "text of the element at fault, or css:<selector>",
            "note": "CTA is outlined blue #2F5BEA; live is filled navy #050A52",
            "note_live": "CTA is filled navy #050A52"}]}
```

- `name` is `<#>-<language>` (`3-german`, `5-chinese-simplified`).
- `anchor_uat` / `anchor_live`, `mark_uat` / `mark_live` when the text differs
  per side. Omit `mark` when the whole component is the issue.
- `"missing_on": "uat"` (or `"live"`) for a missing component, with that
  side's anchor set to the heading just above where it should be.
- `"open": ["<tab title>", "<accordion item title>"]` when the issue sits in
  a tab or accordion item that is closed on load: those are clicked first,
  in order (`open_uat` / `open_live` if the titles differ per side).
  `OPEN NOT FOUND`: retry with the exact visible title.
- `"in_header": true` for a header CTA issue (the header is otherwise skipped
  when looking for the anchor); anchor and mark are the CTA text.

Run `py -3.13 S/capture_issues.py work/<slug>/shots.json` (parallel tabs).
Open every image. If the image does not show the issue, the issue is not
confirmed: fix the anchor/mark and retry once, otherwise drop the issue (or
move it to "Possibly not an issue") and delete its images. `ANCHOR NOT FOUND`
/ `MARK NOT FOUND`: retry with the exact visible text. `LOGIN NEEDED`: mark
the page `login` (`batch.py mark <slug> login --note "..."`) and move on.

## 5. findings.json and the report

Write `work/<slug>/findings.json` (UTF-8):

```json
{"title": "<page H1 or a short name>",
 "issues": [{"id": 1, "component": "Hero (Hero multi-assets)", "kind": "CTA",
             "issue": "Primary CTA is outlined blue, live is filled navy",
             "uat": "#2F5BEA outline", "live": "#050A52 fill",
             "languages": ["English", "German", "French"],
             "shots": {"uat": "screenshots/<slug>/1-english-uat.png",
                       "live": "screenshots/<slug>/1-english-live.png"},
             "cause": "Button variant not mapped",
             "signature": "<the diff lead's sig, or a short kebab key like hero-layout-reversed>"}],
 "not_issues": ["Testimonials carousel shows different people: rotating content."],
 "couldnt_check": ["Form submission not tested."]}
```

- *signature*: for recurring faults use the fixed keys from SKILL.md
  ("Use these fixed signatures"): `hdrnav:0:items`, `hdrnav:1:items`,
  `uat-404-locales`, `uat-content-empty`, `header-cta-404`, `accordion-hash`,
  `tab-url-query`, `heading-h2-no-h1`. Never invent a new name for one of
  these, or the cross-page roll-up misses it.

- Languages as names: English, German, French, Spanish, Japanese, Portuguese,
  Chinese (Simplified), Hungarian, Italian, Korean, Dutch, Polish, Thai,
  Russian, Czech, Chinese (Traditional), Turkish.
- *issue*: one plain sentence. *component*: heading or short name plus type
  if recognisable (Hero multi-assets, Basic Text, Lead Para, Next Step card,
  Customer Logo, Tabs, Accordion, FAQ, Article overview).
- *cause*: from `issue-checklist.md` (same folder as this file); a suggestion.
- Order issues: locale problems first, then missing/extra components, then
  the rest top to bottom of the page.
- Coverage comes from `diff.json` automatically; add a `"coverage"` list only
  to correct it.

Then `py -3.13 S/report.py page <slug>`. It prepends a dated section to
`reports/<slug>.md` (creating it if new). It also writes
`work/<slug>/confluence.html`; ignore it, nothing goes to Confluence.

## 6. Done

`py -3.13 S/batch.py mark <slug> done --issues <N>`
(this also deletes the page's capture slices). On an error you can't fix:
`batch.py mark <slug> failed --note "<reason>"`. Then go back to step 1.

## Ground rules

- Header: compare the menu items of every row (labels, missing / extra,
  order; no mega menus, no menu-link destinations) and the header CTA
  (presence, style, text, final destination). Never report the top bar
  (contact sales, phone, sign in, "Company"). Footer out of scope. Capture
  at 1440px.
- Tabs, accordions and the header: `issue-checklist.md` sections 10-12 list
  what was found before (colours, panel gap, deep-link query/hash, menu
  collapse) and what is not an issue.
- Never report font size or font weight; body text #2D2D2D vs #545454 or
  #050A52; heading/title text #050A52 vs #141414 (accordion/FAQ titles also
  vs #000000), but keep `Accessibility` leads where navy fails WCAG AA on a
  dark background; the expected header CTA design; tab label colours; no
  divider above the first accordion row; heading level on its own;
  lang code variants of the same language; live /ru/ → /ru-cis/; card,
  column or CTA width on its own; spacing differences of 2px or less; links
  that end on the same page.
- Every issue has a UAT value and a live value (hex, px, text, file names).
- Rotating or personalised content goes under "Possibly not an issue".
- Locale mismatches always go in the Issues list.
