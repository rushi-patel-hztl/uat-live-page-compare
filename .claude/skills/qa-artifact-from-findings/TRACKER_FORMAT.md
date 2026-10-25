# QA tracker format

Every UAT-vs-live QA artifact is built in this one format, whether it comes from `build.py` (new run), `tracker/upgrade.py` (older artifact) or the Special pages build in `artifact-special/`. The page is `tracker/src/head.html` + `tracker/src/app.js` with the data as JSON inside `<script type="application/json" id="data">`.

## Page

- **Top:** heading, stats (issues, open blockers, messy pages, locales affected, fix-once groups), a progress bar ("x of y fixed"), a red Messy panel when any page is Messy, the issues-per-page-and-locale heat grid with a Fixed column, then the "Fix once, clears several pages" groups (an accordion, closed by default, with the group count on its header), then All issues.
- **Toolbar filters:** page, locale, issue type (checkboxes), status, severity, "Mine", sort (severity first or original order) and text search. The filters drive the stats and the heat grid.
- **Each issue:** severity and type tags, component, what differs, UAT and live values, locale chips (link to the UAT page in that locale), likely cause, "also on" links, a work strip (status, severity, assignee, "Assign to me", notes) and the UAT/live screenshots.
- **Each fix-once group:** its own status and assignee, a "Fix in" tag (Component, Template, Content, Config) with a short note, and "Apply to all N issues".
- **Re-check:** a "Request re-check" button per page and for all pages. It only records a request; someone runs the `process-qa-rechecks` skill to act on it.
- **Shared state:** status, severity override, assignee, notes and re-check requests are stored in the artifact's `db` capability (collections `issues`, `groups`, `rechecks`). Publish with `{"db": {}, "user": {"scopes": ["profile"]}}` and keep any capability the artifact already stores (for example `assets`). Viewers with view-only access see the state but cannot change it. The state starts empty and belongs to that one artifact.

## Issue types (filter)

An issue can carry several. Order in the filter:

| Type | Meaning |
|---|---|
| Source 404 | Live returns 404 while UAT loads (quick fix: unpublish in Sitecore; Minor) |
| Target 404 | UAT returns 404 while live loads (Blocker) |
| EN Fallback | Live loads (200) but a non-English locale is all English |
| Content Missing | Same component count, something inside a component is missing |
| Component Missing | UAT has fewer components than live (Blocker) |
| Additional Component | UAT has a component live does not have |
| Duplicated Component | A component or the page blocks repeat on UAT (Blocker) |
| Header | Anything about the header component (menu labels, order, header CTA) |
| Missing Image | An image, icon, logo or badge is missing or broken |
| UI | Pure styling or layout: colour, background, alignment, layout, spacing, icon or badge size, corners, accordion or CTA style |
| Other | Everything else (links, URL hash, dropdowns, locale redirects, ...) |

The rules are in `tracker/common.py` (`norm_kind`, `severity`, `is_ui`, `types_of`). Worker rules for choosing the `kind` are in the `uat-live-page-compare` skill (SKILL.md, "Naming missing things" and "Page versions that differ").

## Severity

Blocker: Target 404, Locale (page empty or missing on one side), Duplicated component, Component Missing. Major: Content Missing, EN Fallback, Additional Component, Content, URL, Accordion, Header, CTA, Form, broken table images. Minor: everything else, including Source 404 and pure styling. People can change an issue's severity on the page.

## Messy page (red alarm)

A page is Messy when any one holds: the two sides are different versions (`version_mismatch` in `findings.json`); two or more components are missing or duplicated; a locale loads blank or repeats page blocks; or at least 50% of its sections (pages with 4 or more) have a Blocker or Major issue. Messy issues get a Messy tag and sort first; Messy pages sort first.

## Data fields

`data.pages[].issues[]`: `id, component, kind, issue, uat, live, cause, langs[], shots{uat,live}, also[], group, signature` (input) and, added by `tracker/upgrade.py`: `sig, sev, ui, quick, rc, types[], messy`. `data.pages[].messy {on, why[], sections, affected}`. `data.shared[]`: `id, title, kind, refs[[slug,id]], types[], fix, note`. `data.packs` is true when screenshots are packed (`packs/<slug>.txt`).

## Keeping copies in step

`tracker/` here is the reference copy. `artifact-special/` holds the same code for the Special pages tracker. If you change the page or the rules, change both (copy `common.py`, `upgrade.py`, `src/`).
