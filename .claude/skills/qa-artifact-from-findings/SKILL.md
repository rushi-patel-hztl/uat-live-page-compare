---
name: qa-artifact-from-findings
description: Turn uat-live-page-compare results (work/<slug>/findings.json and reports/screenshots) into ONE shareable QA-log artifact - heat grid of issues per page and locale, "seen on several pages" groups, per-page issues with UAT/live screenshots, clickable locale chips - and merge results that several teammates captured on different machines. Use when the user asks for the artifact, the QA log page, or says teammates ran some of the URLs on their machine and the results must be combined. Handles the 512-file artifact limit by packing screenshots.
---

# QA artifact from findings

Reads the findings that the `uat-live-page-compare` skill writes and builds the QA-log artifact (the same page as "Download pages QA log" / "Solutions pages QA log"). No Confluence involved.

Files in this folder (`S/` below): `build.py`, `export_run.py`, `template.html`.
Run everything from the project folder (the one holding `work/` and `reports/`), with `py -3.13` on Windows.

## A. One person has all the results

1. Pick the pages: `--prefix <slug-prefix>` (every slug in `work/_progress.json` starting with it), `--slugs a,b,c`, or `--slugs-file work/pairs.txt` (one URL or path per line; the last token is used, the locale segment is dropped, `/` becomes `-`). Leave out non-pages with `--exclude` (for example a path that redirects on both sides).
2. Build:
   `py -3.13 S/build.py --out artifact-NAME --title "Solutions pages QA log" --heading "TeamViewer solutions pages: internal vs live" --slugs-file work/pairs.txt --exclude solutions`
   The title is the artifact name: two to four words, no colon-explainer. It prints page, issue and shared-group counts and writes `artifact-NAME/index.html`, `artifact-NAME/packs/<slug>.txt` and `artifact-NAME/publish_batches.json`.
3. Review `index.html`'s JSON only if something looks off (labels come from the slug; the intro and the heat note are generated). Check the counts against the reports.
4. Publish with the Artifact tool (load `artifact-design` first, as the tool says):
   - First call: `file_path` = `artifact-NAME/index.html`, `icon` "chart", one-sentence `description`, `root` = `artifact-NAME`, `files` = the first list in `publish_batches.json` (paste the list; the paths are relative to `root`).
   - Each further batch: same `file_path`, `url` = the artifact's URL, `root`, `files` = the next list. Files from earlier calls are kept.
   - To make a new artifact rather than update one, publish from a different folder (the same `file_path` always updates the existing artifact).
5. `Artifact` action `open`, then report page/issue counts and that it is private until shared.

Why packs: one artifact holds at most 512 files, and a run has 1,000+ screenshots. `build.py` recompresses the screenshots to JPEG (1280px wide) and stores one base64 text file per page; the page fetches a page's pack when you scroll to it and shows the images from blob URLs. The host serves only standard types, so the packs are `.txt`, not `.bin` or `.zip`.

## B. Several people ran different URLs on their own machines

Each teammate, after their `uat-live-page-compare` run, from their project folder:
`py -3.13 S/export_run.py my-run.zip --slugs-file work/pairs.txt` (or `--prefix ...`). It zips each page's `findings.json`, `plan.json`, report and screenshots. Send the zip to whoever builds the artifact.

The builder unzips every teammate's zip into the same project folder (the layout is identical, slugs do not clash if the URLs differ), puts all URLs into one `work/pairs-all.txt`, and runs step 2 onwards of section A. If two people ran the same page, keep the newer `findings.json` and delete the other's `reports/screenshots/<slug>/` first, so old screenshots do not mix in.

## Before a teammate captures pages

These cost the first run hours, so tell teammates up front:
- The live site (Cloudflare) rate-limits one machine. 16 tabs and even 4 tabs triggered HTTP 429 / "Error 1015" within about 12 pages. Use `batch.py capture --concurrency 1` and a pause of about a minute between pages, and keep analysis browsing at concurrency 1.
- Check `work/<slug>/*-live.txt` for "Error 1015", "Access denied" or "Too Many Requests" before trusting a capture; a poisoned page shows live 404s everywhere. Re-queue it with `batch.py mark <slug> pending`.
- If blocked, wait (it cleared after roughly 2 hours) or ask the web team to allowlist the machine. A request header token and rotating IPs are not the fix and the second is evasion; do not do it.
- In Git Bash a leading `/en/...` argument is rewritten to a Windows path; quote it or set `MSYS_NO_PATHCONV=1`.
- A path such as `/en/solutions/` can redirect both sides to regional homepages; if every locale lands on a homepage, the page is not comparable.

## Caveats to repeat in the hand-off
Per-locale "missing section" findings usually come from capture snapshots, and style findings were mostly confirmed in English only. Videos, dropdowns, anchors and CTA redirects are not re-checked unless a worker did so. Check "UAT not translated" leads against live's own language before believing them.
