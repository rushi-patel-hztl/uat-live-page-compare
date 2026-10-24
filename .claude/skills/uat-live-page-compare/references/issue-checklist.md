# Issue checklist

These are the issue types that come up again and again when a migrated page is
checked against live. For each: what to look for in the `extract.js` JSON, and
the usual cause and owner. Owners are suggestions for the team to confirm.

Owner labels:
- **Content / Manual**: fixable by an author in the CMS (missing language
  version, empty field, wrong option chosen).
- **Migration**: the migration mapping is wrong (style or theme id not mapped,
  component mapped twice, field not migrated). Needs a mapping fix and re-push.
- **DEV**: front-end or rendering bug (CSS, component logic, missing field in
  the component).
- **Needs discussion**: unclear whether it's intended, or no field exists to
  support it.

## 1. Components missing, extra or duplicated

| Look for | Usual cause | Owner |
|---|---|---|
| A live component with no UAT match in one locale, but present in another locale | Item has no version in that language | Content / Manual |
| UAT page has 0–1 components, or `text` is empty | Language version missing or page not published | Content / Manual |
| The same heading/text appears in two consecutive UAT components (two Basic Text, two Hero, Lead Para twice) | Component mapped twice in presentation details, or a fallback + real version both rendered | Migration (re-push) |
| A live component (article overview, dynamic article list, form) has no UAT counterpart in any locale | Component not rendering or datasource missing | DEV, or Manual if datasource is empty |
| Extra component on UAT with no live counterpart | Could be intentional new content; check with the user | Needs discussion / possibly not an issue |
| UAT redirects to another page, or `status404` true | Page or language missing, redirect rule wrong | Content / Manual, or DEV for redirects |
| `lang` doesn't match the locale, or de/fr text is English | Language fallback is serving en | Content / Manual |

## 2. Alignment

| Look for | Usual cause | Owner |
|---|---|---|
| Heading or text `centred: true` on live but `false` on UAT (or `align` differs) | Alignment style id not mapped (e.g. content alignment field on Hero multi-assets) | Migration |
| Tab titles not centred | Tab component style option not set | Content / Manual |
| CTA in a different position (below vs beside text) | Layout variant not mapped | Migration |
| Cards/headshots not on one line | Column/grid variant missing | DEV |

## 3. Spacing

Compare `gapBelow`, `mt`, `mb`, `pt`, `pb` for paired components. Differences
over 2px are findings.

| Look for | Usual cause | Owner |
|---|---|---|
| Large extra gap where UAT has a component with no visible text (empty Lead Para, empty Basic Text) | Empty component placed on the page | Content / Manual |
| Consistently different gap on every component | Spacing/theme style not mapped | Migration |
| Single component's padding differs | Component CSS | DEV |

## 4. Colours and backgrounds

| Look for | Usual cause | Owner |
|---|---|---|
| Text `color` differs for the same text | Theme mapping (e.g. dark theme mapped instead of default) | Migration |
| Component `bg` differs, or `bgImg` present on live but null on UAT | Background/theme option not mapped, or image missing in the media library | Migration, or Manual for image |
| Card backgrounds should be white / shouldn't be grey | Card theme option | Needs discussion if live has no equivalent setting |
| Customer logo strip background differs | Background option not configured | Content / Manual |

## 5. CTAs

| Look for | Usual cause | Owner |
|---|---|---|
| `looksPlain: true` on UAT, styled on live | Link field migrated without the button style | Migration |
| `bg`, `color` or `border` differ | Button variant/theme mapping | Migration |
| `icon` true on live, false on UAT (arrow missing) | Icon option not mapped | Migration |
| CTA missing on UAT | Link field empty in that language | Content / Manual |
| CTA or card link ends on a different page (compare the final page after redirects, not the raw `href`) | Link not updated after migration | Content / Manual |
| Tooltip missing | Field not configured on the item | Needs discussion |

## 6. Images and icons

| Look for | Usual cause | Owner |
|---|---|---|
| `broken: true` on UAT | Media item missing or not published | Content / Manual |
| Image on live with no matching file on UAT | Image not migrated | Content / Manual |
| Same image noticeably smaller on UAT (`w`/`h`), e.g. headshots, Next Step icons | Image size variant / CSS | DEV |
| Icons missing in Next Step cards | Icon field not mapped | Migration, or Manual |
| `alt` differs | Alt text not migrated | Content / Manual |

## 7. Borders, outlines, list styles

| Look for | Usual cause | Owner |
|---|---|---|
| `border` on live but null on UAT (cards, outlined components) or the reverse | Border/outline style option | DEV (needs discussion if no field) |
| RTE list shows bullets instead of checkmarks | RTE list style class not applied | Content / Manual |
| FAQ items have borders that live doesn't | Component CSS | Needs discussion / DEV |

## 8. Default states

| Look for | Usual cause | Owner |
|---|---|---|
| Different tab `active` on load | Default tab setting | Content / Manual |
| Different accordion item `open` on load | Default-expanded setting | Content / Manual |

## 9. Content text

Diff `text` and `headings` of each pair. Report changed words, not the whole
paragraph. Wording that differs only by whitespace or punctuation is not a
finding.

| Look for | Usual cause | Owner |
|---|---|---|
| Different or missing text | Field not migrated or edited since | Content / Manual |
| Pretitle/eyebrow missing | No field on the target component | Needs discussion / DEV |
| Link destinations differ after redirects (same final page = not a finding) | Link not updated | Content / Manual |

## 10. Tabs

Every tab is clicked during capture (`TAB "<title>" url=…` lines with the
panel's own `· T / CTA / IMG / TXT` lines).

| Look for | Usual cause | Owner |
|---|---|---|
| Active / inactive tab label colour differs (seen: UAT #3056EF / #27272A, live #050A52 / #545454) | Tab component theme | DEV |
| Heading inside the tab panel centred on one side, left on the other | Alignment style id not mapped | Migration |
| Heading inside the panel is a different level (H2 vs H3): the panel lands in another block | Heading level option not mapped | Migration |
| Tab does not switch when clicked on UAT | Tab script / component bug | DEV |
| `url=` after a click differs (live sets `?tab=remote-support`, UAT doesn't, or a different value) | Tab deep-link (query) not implemented | DEV |
| Different tab open on load, or the page's `?tab=` query not honoured | Default tab setting / query handling | Content / Manual, or DEV |
| Panel content, CTAs or images differ for one tab only | That tab's datasource or language version | Content / Manual |

Not issues: both sides setting the same `?tab=` value; the site scrolling to the
tabs on load when the URL has `?tab=` (capture resets the scroll).

## 11. Accordions

Every closed item is expanded, captured and closed again (`ACCI "<title>"
url=…` lines). Items inside a tab that is closed on load are not expanded by
the capture: open the tab first (`"open": ["<tab>", "<item>"]` in shots.json).

| Look for | Usual cause | Owner |
|---|---|---|
| Item title colour differs (seen: UAT #050A52, live #000000) | Accordion component theme | DEV |
| Large gap between an expanded item's title and its content (seen: 88-114px vs 16px) | Component CSS | DEV |
| Inline links in the item's rich text coloured (seen: UAT #3056EF, live #141414) | RTE link style | DEV |
| `url=` after expanding: live adds a hash (e.g. `#multipleaccordion-…-item-…`) that re-opens the item when the link is loaded, UAT adds none | Accordion deep-link not implemented | DEV |
| Item does not expand when clicked on UAT | Component script bug | DEV |
| Article / "Vollständigen Artikel anzeigen" CTA goes to another language (`/en/` on a `/de/` page) | Link not updated after migration | Content / Manual |
| Images in items have empty `alt` | Alt text not migrated | Content / Manual |
| Item CTAs open in the same tab where live uses a new tab (`target=_blank`) | Link target not migrated | Migration |
| Item missing / extra, or open on load on one side only | Item not migrated / default-expanded setting | Content / Manual |

Not issues: "(Opens in a new tab)" screen-reader text (1x1px) after links;
video thumbnails that lazy-load more slowly but appear; live CTAs pointing to a
step anchor (`#schritt-2`) of the same article UAT links to (same final page:
list under "Possibly not an issue").

## 12. Header (menu items and header CTA)

Pages are captured at 1440px so the full header shows. Capture lists each menu
row (`HEADER NAV main menu: …`, `HEADER NAV second row: …`) and the styled
header button (`HEADER CTA …`). Top-bar utility links (contact sales, phone,
sign in) are skipped. Mega menus are not opened.

| Look for | Usual cause | Owner |
|---|---|---|
| Menu item labels show raw page names / slugs (`world-class-privacy`) where live has a label ("Data protection") | Navigation title field not filled; item name used as fallback | Content / Manual |
| Menu item on one side only, or a different label | Navigation item not migrated / not hidden from navigation | Content / Manual |
| Menu items in a different order | Item sort order in the CMS | Content / Manual |
| Second menu row (section navigation) on one side only | Context / secondary navigation not configured | DEV, or Content / Manual |
| Header CTA (Download, Book a demo, Beratungstermin vereinbaren) on one side only | Header CTA not configured / not migrated | Content / Manual |
| Header CTA style or text differs | Button variant not mapped | Migration |
| Header CTA ends on a different page, or opens in a new tab on one side only | Link not updated / target not migrated | Content / Manual |

Never report: the top bar (contact sales, phone, sign in, "Company"), the
destinations of menu items, or the menu collapsing below 1440px.

Accepted colour and heading differences anywhere on the page (confirmed false
alarms, never report them): body text #2D2D2D on UAT vs #545454 or navy #050A52
on live (e.g. hero body text); heading or card-title text navy #050A52 on UAT
vs near-black #141414 on live (e.g. integration card titles); a heading level
that differs on its own (H5 on UAT vs H3 on live).

## 13. Status: 404, 301 and redirects

Decide this first, per locale (SKILL.md "Status rules").

| Look for | Result | Owner |
|---|---|---|
| 404 on both internal and live | Expected behaviour, not an issue | n/a |
| 404 on one side only | Issue, no comparison for that locale | Content / Manual, or DEV |
| 301 or 302 on both sides | Expected behaviour, not an issue (list destinations) | n/a |
| 301 or 302 on one side only | Issue with the redirect destination, no comparison | DEV (redirect rule) or Content / Manual |
| Live redirects to another page, internal loads | Don't validate; report only where live redirects to | Needs discussion |
| Internal redirects and ends on a 404 or a different page, live loads or ends on a working page (seen: `/products/remote/pricing` → 302 `/apac/overview` → 301 → 404) | Issue: give the full chain, no comparison | DEV (redirect rule) |
| `ERR_HTTP_RESPONSE_CODE_FAILURE` in the capture log | The page answered 404 or another error status; read the coverage table | n/a |

## 14. CTA redirection and dropdowns

| Look for | Usual cause | Owner |
|---|---|---|
| CTA's final page (after redirects) differs from live | Link not updated after migration | Content / Manual |
| CTA ends on a 404 on internal | Target page missing / link wrong | Content / Manual |
| CTA opens in a new tab on one side only (`target=_blank`) | Link target not migrated | Migration |
| Dropdown options differ (text, order, count) or default value differs | Datasource / list not migrated | Content / Manual |
| Dropdown doesn't open, or choosing an option does nothing on internal | Component script | DEV |
| Dropdown style differs (border, arrow icon, colours, spacing) | Component CSS | DEV |

## 15. Videos

| Look for | Usual cause | Owner |
|---|---|---|
| Video or play button on live, missing on internal | Video field not migrated | Migration, or Content / Manual |
| Play button doesn't play or open the video | Component script / modal | DEV |
| Different video source (YouTube / Vimeo id or file) | Wrong video in the field | Content / Manual |
| Thumbnail missing or different | Poster image not migrated | Content / Manual |
| Controls, autoplay / mute or modal vs inline behaviour differ | Video option not mapped | Migration |

## 16. Anchor links (same-page links)

Use live in the same locale as the reference. Do not check landing position
or sticky-header offset.

| Look for | Usual cause | Owner |
|---|---|---|
| Anchor's target id missing on internal (click does nothing) | Component anchor id not migrated | Migration, or Content / Manual |
| Click scrolls to a different component than on live | Anchor id on the wrong component | Content / Manual |
| In-page nav has different, missing or reordered anchor links | Anchor list not migrated | Content / Manual |
