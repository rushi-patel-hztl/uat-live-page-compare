---
name: uat-live-page-compare
description: Compare UAT/staging/internal pages against their live counterparts in all 17 site locales (EN, DE, FR, ES, JA, PT, CN, HU, IT, KO, NL, PL, TH, RU, CS, TW, TR) and log every difference in UI (spacing between components, text colour, CTA colour and style, alignment, images, icons, borders, backgrounds) and content (missing, extra or duplicated components, text, links, every tab and accordion item opened including the URL query/hash they set, untranslated or missing language versions), excluding header and footer apart from the top-right header CTAs. Built for volume - one page or thousands - with parallel capture, parallel analysis agents, a live progress bar, issues grouped across languages and pages, Markdown reports and one shareable QA tracker artifact for the run. Use this whenever someone pastes a UAT or internal URL together with a live URL, pastes or attaches a list of URL pairs, asks to "compare UAT with live", "check this page against production", "find the UAT issues", "do the visual QA", "check the migration for these pages", "is UAT matching live", or wants findings for a UAT issues log or QA artifact, even if they only paste two links with no instruction. Also use for Sitecore / XM Cloud / headless migration QA where pages are checked against the old site.
---

# UAT vs live page comparison (batch, parallel)

You are the **orchestrator**. Scripts do the mechanical work (open pages,
measure, pre-compare, screenshot, render reports); **worker agents** running
in parallel do the judgement (confirm each difference on screen, group,
write findings); you keep the progress bar and the common-issues roll-up, and publish the
QA tracker artifact at the end.

Pages are opened with **Playwright** in the installed Chrome. Never use the
Claude in Chrome tools. Run every script from the project folder with
`py -3.13` (Windows; `python` elsewhere): the scripts write `work/` and
`reports/` under the current folder. Scripts live in the `scripts/` folder
next to this SKILL.md; `S/` below means that folder's absolute path, and
`R/` the `references/` folder beside it.

```
work/_progress.json        registry: every page, its status, issue count
work/<slug>/plan.json      the 17 locale URLs on each side
work/<slug>/<code>-uat.json|.txt, <code>-live.json|.txt   snapshots
work/<slug>/en-uat-01.jpg …  full-page slices (EN only by default)
work/<slug>/diff.md        machine leads, grouped across locales
work/<slug>/findings.json  confirmed issues (written by the worker)
reports/<slug>.md          the report (newest dated section on top)
reports/_common-issues.md  issues that recur across pages
reports/screenshots/<slug>/  annotated UAT + live image per issue
```

No Excel and no Confluence. Markdown reports and the QA tracker artifact only.

## Step 0: Prerequisites (once per machine, not per task)

If memory says the prerequisites were verified, skip this step. Otherwise run
`py -3.13 S/check_prereqs.py`. If everything passes, save a memory saying so (date,
versions) so later tasks skip this. If something fails, tell the user exactly
what to install (`pip install playwright pillow`; the installed Chrome is
used, no browser download) and stop.

## Step 1: No Confluence

Results never go to Confluence, and don't ask the user for a Confluence page.
The deliverable is the QA tracker artifact built in Step 5. Workers skip the
Confluence step of `R/analyse-page.md`.

## Step 2: Plan

Put the user's pages in `work/pairs.txt`, one per line: `<UAT URL> <live URL>`
(if they gave a file or a pasted list, convert it; if they gave only UAT URLs,
derive live by swapping the host and say so). Then:

```
py -3.13 S/batch.py plan work/pairs.txt
```

It reads each live page's hreflang links (in parallel), picks the main
version of each of the 17 languages (e.g. `/en/` not `/en-mea/`, `/latam/`
only when there is no `/es/`), builds the internal URL on the same path
(live `/ru-cis/` → internal `/ru/`), guesses unlisted locales from the site's
segment pattern (flagged "Listed on live: NO", still checked), and registers
every page as `pending`. Pages already in the registry are skipped, so the
same file can be re-run to add pages. Pass `--locales EN,DE` only if the user
asked for fewer languages.

Slugs are the live path without the locale, joined with `-`
(`/en/products/remote/` → `products-remote`), reusing an existing
`reports/<last-segment>.md` if that is what earlier runs used.

## Step 3: Capture (background, parallel)

```
py -3.13 S/batch.py capture --concurrency 12
```

Run it **in the background**. One headless Chrome, 12 tabs; ~2 s per page
load, so ~70 s per page for 34 loads. For hundreds of pages start 2-3
processes at once with `--shard 1/3`, `--shard 2/3`, `--shard 3/3` (watch CPU;
drop concurrency if pages start timing out). For each locale it saves a
snapshot (colours, alignment, gaps, CTAs, images, tabs, text per h1/h2
section; every tab is clicked and every accordion item expanded so their
content is captured and compared too, along with the URL query/hash each
click leaves, then the page is put back in its load state; plus the
main navigation's top-right CTA) and, for EN, full-page slices; when a page's last locale is in, it
runs `diff.py`, which writes `diff.md` and marks the page `captured`. Workers
can start on captured pages while capture continues.

A `LOGIN NEEDED <slug>` line (status `login`): stop launching work for those
pages and ask the user to log in. Run `py -3.13 S/browse.py --login <URL>` in
the background; a visible Chrome opens, the user logs in and closes it, and
the cookies are saved to `.playwright-profile/state.json` for every later
run. Then re-run capture (it picks up `pending` and `login` pages). Never
type credentials.

## Step 4: Analyse with parallel workers

As soon as `batch.py progress` shows captured pages, launch worker agents
with the Agent tool (`general-purpose`), **all in one message** so they run
concurrently, as many as there is work for, up to 10 at a time. Each worker
claims pages itself (`batch.py next 1` is atomic), so two workers never get
the same page. Worker prompt (fill in the brackets):

> You are a UAT-vs-live worker in C:\…\<project folder>; run commands from
> there. Read `<absolute R/ path>/analyse-page.md` and follow it exactly;
> `S/` is `<absolute S/ path>`. No Confluence.
> Process up to 3 pages, then stop. Return only one line per page:
> `<slug> | <N> issues | <top 2 issues, short>`.

Every time a worker returns:

1. Run `py -3.13 S/batch.py progress` and show the bar to the user with the
   worker's lines, e.g.

   ```
   [█████████░░░░░░░░░░░░░░░░░░░░░] 9/30 pages done (30%) | 6 analysing · 4 captured, waiting · 11 to capture · 0 failed · 0 need login | 87 issues so far
   ✓ products-remote | 14 issues | CTA style not mapped; FAQ spacing
   ```
2. Run `py -3.13 S/report.py common` (at most once per returning worker,
   not per page).
3. If pages are still `captured` (or capture is still running), launch a
   replacement worker straight away so the pool stays full.

If capture is still running and no page is `captured` yet, wait for the
capture output rather than launching idle workers. A worker that hits an
error marks its page `failed` with a note; report failed pages at the end and
offer to retry them (`batch.py mark <slug> captured`).

**Single page or a handful:** same pipeline, but you may analyse the pages
yourself (follow `R/analyse-page.md`) instead of launching workers,
and show the full Issues table in the terminal.

## Step 5: Finish

When everything is done (or the user stops):

- Show the final progress bar, the per-page one-liners, and the top common
  issues from `reports/_common-issues.md` (issue, number of pages, languages).
- Build and publish the QA tracker artifact with the `qa-artifact-from-findings`
  skill (section A), over every page in `work/pairs.txt`. Keep pages with 0
  issues in it, such as a URL that redirects to the same page on both sides:
  before building, set `"page_note"` (one sentence: where both sides go and
  why there is nothing to compare) and `"page_note_tag"` (a short label, e.g.
  "Redirects on both sides") in that page's `findings.json`, so the heat grid
  shows the page with its label and the URL count stays complete.
- Give the artifact link and the paths: `reports/<slug>.md` per page and
  `reports/_common-issues.md`.
- List anything in `failed` or `login` with the reason.

## Grouping rules (apply everywhere)

- **One root cause = one issue.** Every CTA with the same wrong style on a
  page is one issue ("all primary CTAs"), not one per button.
- **Same issue in several languages = one row** with a Languages column
  listing them all (e.g. "English, German, French (3/17)"). Screenshots for
  one representative language (English if affected).
- **Same issue on several pages** is rolled up in `reports/_common-issues.md`
  by `report.py common`, which matches issues by
  their `signature`. Give an issue the diff lead's `sig` whenever it came from
  a lead, so the same fault on different pages groups together.
- **Use these fixed signatures** for faults that recur across pages, even when
  you found them without a lead (in an earlier run, workers made up their own
  names, and the roll-up missed the same header fault on 8 pages):
  `hdrnav:0:items` (main menu differs), `hdrnav:1:items` (second menu row
  differs or shows raw slugs), `uat-404-locales` (UAT 404 where live loads,
  any number of locales), `uat-content-empty` (UAT loads but its components
  are empty), `header-cta-404` (header CTA ends on a 404 page),
  `accordion-hash` (expanding an item doesn't set the URL hash),
  `tab-url-query` (clicking a tab doesn't set the URL query),
  `heading-h2-no-h1` (page has no H1).

## Status rules: 404, 301 and redirects (decide first, per locale)

Settle each locale's status before comparing anything. Use the HTTP status
and final URL from the coverage table in `diff.md` (or `browse.py`).

| Internal | Live | Result |
|---|---|---|
| 404 | 404 | **Expected behaviour.** Not an issue; list it in coverage. |
| 404 | loads (or the reverse) | **Issue.** Report it, **no comparison** for that locale. |
| 301 / 302 | 301 / 302 | **Expected behaviour.** Not an issue; list both destinations (a 301 on one side and a 302 on the other still counts). |
| 301 / 302 | no redirect (or the reverse) | **Issue.** Report it with where the 301/302 goes, **no comparison**. |
| loads | redirects to another page | **Don't validate.** Only report where live redirects to. |
| redirects, ends on a 404 (or another page) | loads, or redirects to a working page | **Issue.** Report the whole redirect chain and the final status (e.g. `302 → /apac/overview → 301 → 404`), **no comparison**. Both sides redirecting is only expected when both end on the same working page. |

Only locales where both sides load the same page get the full comparison.

**EN Fallback Issue.** When a non-English locale's live page loads (200) but its
whole content is in English, the locale is falling back to EN on live. If UAT
differs in that locale (translated text, blank or empty sections, different
components), the cause is almost always the fallback, so report **one** issue
per page: kind `EN Fallback`, signature `locale-en-fallback`, listing the
locales and what UAT shows instead. Drop the text, content and missing/extra
component leads for those locales (they all follow from the fallback) and keep
only structural and styling leads. When both sides are English and nothing
differs, it is not an issue; list it in coverage.

## What every comparison covers

Content, UI, spacing, icons (including icon size), alignment, colours, CTAs,
images, borders, backgrounds, tabs, accordions, and also:

- **Dropdowns** (selects, filter menus, custom dropdowns): open each one on
  both sides and compare the options (text, order, count), the default
  value, the style, and what choosing an option does.
- **CTA redirection**: follow every CTA and link to its final page on both
  sides. Report one that ends on a different page, 404s, or opens in a new
  tab on one side only (`target=_blank`).
- **Videos** (including video CTAs and play buttons): the video is present,
  the play button plays it or opens it, the source (YouTube / Vimeo id or
  file) matches live, and the thumbnail, controls, autoplay / mute and modal
  behaviour match.
- **Anchor links** (`#id` links that scroll to another component on the same
  page): the target exists, clicking scrolls to the same component as on
  live, and the set and order of anchor links match live. Use live as the
  reference in each locale: internal DE anchors against live DE anchors,
  and so on. **Do not check landing position or sticky-header offset.**
- **Every locale the site has**, not only EN/DE/FR: missing on one side or
  untranslated is an issue.

The capture does not record dropdowns, videos or anchor links, so check them
on screen with `browse.py` (a `js` expression per page) for every locale.
`R/issue-checklist.md` sections 13-16 list what to look for.

## Comparison ground rules

- Report only differences you measured or saw. Every finding has the UAT
  value and the live value.
- **Pages are captured at 1440px wide** (both sides) so the header shows in
  full; don't compare at a narrower desktop width.
- Header: compare **the navigation menu items** and **the header CTA**.
  - Menu items: every menu row (the main menu, and a second row such as a
    section's own navigation, e.g. Trust Center > Overview, Security
    posture...): labels, items missing or extra, and order. Don't open the
    mega menus and don't follow menu links.
  - Header CTA (styled button on the right, e.g. "Beratungstermin
    vereinbaren", "Kostenloser Download"): present on one side only, style,
    text, final destination after redirects, new tab.
  - Never report the top-bar utility links (contact sales, phone, sign in,
    "Company"). The footer is out of scope.
  - The header CTA design differs by design: UAT `#050A52` text, transparent,
    1px `#050A52` border, 8px radius vs live `#050A52` text, `#FFFFFF`, 1px
    `#3056EF` border, 4px radius (e.g. "Request a trial", "Start free trial").
    Never report that style difference; still report a CTA on one side only,
    different text or a different destination.
- Tabs and accordions: test only the **presence** of the URL query and hash
  after clicking a tab or expanding an item. Report it when one side sets a
  query (or a hash) and the other sets none. A different value is expected,
  not an issue (e.g. UAT `#how-quickly-to-see-value` vs live
  `#qalist-e7b7e9fc40-item-fc0c405042`, or `?tab=a` vs `?tab=b`).
- Never report the 'Number of Employees' form dropdown ranges: UAT `1 - 4 |
  5 - 24 | 25 - 49 | 50 - 99 | 100 - 499 | 500 - 1000 | 1000 +` vs live
  `1 - 5 | 5 - 25 | 25 - 50 | 50 - 100 | 100 - 500 | 500 - 1000 | 1000 +` is
  expected. Still report a dropdown that is missing, doesn't open or doesn't
  submit.
- Never report the decorative hand-drawn / curved arrow illustration beside
  or above a contact form being missing on UAT (live has it): expected per
  design. Other form differences are still reported on their own.
- **Never report font size or font weight differences.**
- Never report body text #2D2D2D (UAT) vs #545454 or #050A52 (live).
- Never report heading/title text #050A52 navy (UAT) vs #141414 near-black
  (live), e.g. feature card titles, nor accordion/FAQ item titles #050A52
  (UAT) vs #141414 or #000000 (live), nor a heading level difference on its
  own (H5 vs H3). Navy is the expected title colour, so these are false alarms.
- Never report tab label colours: UAT active #3056EF / inactive #27272A
  (or #474747) vs live navy #050A52 / #545454 is expected per design.
- Never report a missing divider above the first accordion row (UAT has
  none, live has a 1px line): expected per design.
- **Exception: navy on a dark background.** Where a navy #050A52 title sits
  on a dark background, it must pass WCAG AA contrast (4.5:1, or 3:1 for
  large text: 24px+, or 18.66px+ bold). Report it as kind `Accessibility`
  with the ratio, e.g. `#050A52 on #141F6B (1.2:1)` vs `AA 4.5:1`.
- Never report `<html lang>` code variants of the same language (`zh` vs
  `zh-CN`, `zh-TW` vs `zh-HK`). Do report content in the wrong language.
- Never report live `/ru/` → `/ru-cis/` vs internal `/ru/`. Compare RU content
  against live `/ru-cis/`.
- Never report card or column width differences on their own, or CTA width.
- Ignore spacing differences of 2px or less.
- Links: compare the final page after redirects, not the raw href.
- Compare component to component: find each live component anywhere on UAT
  (tabs, lazy content) before calling it missing.
- Rotating/personalised content (carousels, dates, testimonials order) goes
  under "Possibly not an issue".
- Locale mismatches (loads on one side only, redirects elsewhere, wrong
  language) always go in the Issues table.

## Naming missing things: count components first

Count the components on each side (the `blocks=` figure in the snapshot header
and the `#n` sections), then choose the kind:

- **Same component count, something inside a component is missing** (eyebrow,
  subheading, text, image, caption, field): kind `Content Missing`.
- **UAT has fewer components than live** (a whole component is absent): kind
  `Component Missing`.
- **UAT has more components than live** (a component that live does not have):
  kind `Additional Component`.
- A component repeated on UAT stays `Duplicated component`.

A difference inside a component that is not "missing" (wrong text, other
colour) keeps its usual kind (`Content`, `Colour`, ...).

**Header issue.** Anything about the header component (menu labels, items,
order, the top-right header CTA) is kind `Header` (component text starting
"Header"); the QA tracker tags it as a Header issue so it can be filtered on
its own, even when it is also a styling difference.

**UI tag.** Pure styling and layout differences (colour, background, alignment,
layout, spacing, icon or badge size, image corners, accordion or CTA style) are
tagged UI by the QA tracker so the migration team can hide them and work on
the rest. Text link styling (link colour, underline or weight, e.g. live blue
vs UAT black) is always UI and Major: keep the `linkcolor:` / `linkstyle:`
lead signature and say "link colour" in the sentence. Other text colour
differences (titles, headings, labels, body copy)
are tagged Font Colour instead, or as well when the same issue also changes
background, border, spacing or layout; say "text colour" or "title colour" in
the issue sentence so the tracker can tell. Use one of the kinds `UI`, `Colour`, `Background`, `Alignment`,
`Layout`, `Spacing / heading`, `Accordion style` for them. Broken or different
images (an asset problem) and anything about content, links or structure are
not UI. Before calling a
component missing or additional, search the other side for it (SKILL.md,
"Compare component to component").

## Page versions that differ, and the Messy flag

- **Both sides load but are different versions of the page** (for example UAT
  has the pre-event page and live the post-event page): report it as one issue
  with signature `version-mismatch`, set `"version_mismatch": true` in
  `findings.json`, and **keep comparing**. Every component that exists on both
  sides still gets the styling, dropdown, video, anchor and CTA checks, and
  components found on one side only are reported as missing or extra. Never
  skip checks because the versions differ, and never end by asking the user
  whether to continue.
- **Messy** is a page-level alarm that the QA tracker (`artifact-special/build.py`)
  computes from `findings.json`. A page is Messy when any one holds: the two
  sides are different versions (`version_mismatch`); two or more components are
  missing or duplicated (`kind` "Missing component" or "Duplicated component");
  a locale loads blank or repeats page blocks (signature `locale-<xx>-empty` or
  the dedup group); or at least 50% of the page's sections have a Blocker or
  Major issue, on pages with 4 or more sections. Use those `kind` values and
  signatures consistently so the flag is computed correctly.

## Site behaviours seen in earlier runs

- Live URLs with `?tab=…` keep that query in the plan (hreflang links drop it),
  and the site scrolls to the tabs on load; capture scrolls back to the top
  before screenshots.
- Some pages make `<body>` its own scroll area; `pw.py` forces
  `overflow: visible` on `html, body` so the window scrolls and full-page
  screenshots aren't cut. If a slice still starts mid-page, check
  `document.body.scrollTop`.
- Images inside accordion items lazy-load; `capture_issues.py` waits up to 3 s
  after opening, so a missing thumbnail in a shot is not an issue until checked.
- The sites may reset connections after many loads (`ERR_CONNECTION_RESET`,
  `ERR_ABORTED`); retry with `--concurrency 1`.
- `FAILED: … ERR_HTTP_RESPONSE_CODE_FAILURE` in the capture log is the UAT
  page answering 404 (or another error status), not a capture fault. Read the
  coverage table in `diff.md` and apply the status rules; don't re-capture.
- On uat-sitecore.teamviewer.com, pages that aren't published in a language
  return 404, or load with empty components, in most locales other than EN
  and DE. Report each as one issue per page (`uat-404-locales`,
  `uat-content-empty`) listing the locales, not one issue per locale.
- Seen on uat-sitecore: the header "Try now for free" CTA links to
  `/en/sitecore/` (404), and the second menu row shows raw slugs (`remote`,
  `add-ons`, …) in alphabetical order. Expect these on most product pages.

`R/issue-checklist.md` lists the typical issue types, likely causes
and owners; sections 10-12 cover tabs, accordions and the header.
