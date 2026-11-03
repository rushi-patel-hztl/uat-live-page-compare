---
name: qa-tv-retest-from-report
description: Re-test every issue in an existing TeamViewer UAT-vs-live QA log artifact against the current www.teamviewer.com (now serving the Sitecore build after go-live), mark each one fixed / partly / still / couldn't check, and publish a NEW tracker artifact with the statuses written, plus optionally a second artifact with only the issues still open. Leaves the old artifact untouched. Use when the user pastes a QA log / tracker artifact link and asks to re-check or retest it against www, says "go-live re-check", "retest from report", "which of these are fixed on www now", or wants an open-issues-only version of a re-checked log.
---

# Re-test a QA log artifact against www

The old log compared internal.teamviewer.com (UAT) with the old www (live). www now serves the Sitecore build, so for each old issue the old **UAT value is the fault** and the old **live value is the expected result**. Every page is re-captured on www in all 17 locales and each issue is judged against that.

Confirm the artifact link with the user before starting. Once you've started, the run is slow and writes a new artifact.

Run from the project root. Python is `python3` on macOS (3.9 works) and `py -3.13` on Windows. Below, `K` = `.claude/skills/qa-tv-retest-from-report/scripts`, `SP` = the session scratchpad, and `<name>` is a short slug for the log (e.g. `usecases3`). Use a fresh work folder per run (`work/_golive-<name>`) so runs don't overwrite each other.

## 1. Read the old artifact

1. Call `Artifact` `read` with the link. It saves the full HTML; copy that file to `SP/old.html`.
2. Run `python3 K/extract.py SP/old.html SP work/_golive-<name>`. This writes `SP/old_data.json` and `work/_golive-<name>/<slug>/old_issues.json` for every page.
3. Run `Artifact` `list` with `scope: "files"` on the old URL to get its `shots/...` paths.

## 2. Capture www in all 17 locales

Run `python3 K/capture.py SP/old_data.json 16 work/_golive-<name>` in the background.

- It loads the live EN URL with `/en/` swapped for each locale. RU uses `ru-cis`; the others use the two-letter code.
- EN also gets screenshot slices.
- Pages with no issues are skipped.

16 tabs captured 187 loads in about 6 minutes with no failures. Use more only if the user asks for maximum speed.

When it finishes:
- Re-run with `--missing` at 2 tabs for any locale with no `<CODE>-now.json`. Timeouts usually mean rate limiting.
- `grep -l "Error 1015\|Too Many Requests" work/_golive-<name>/*/*-now.txt`. Re-capture any file it lists.
- If a long EN page fails with "Unable to capture screenshot", its JSON is still saved. Skip the slices for that page.
- A 404 is not a failure. It is the expected result for Source 404 issues.

## 3. Verify with parallel agents

Launch general-purpose agents in ONE message, each with 1–3 pages, balanced by issue count. Each agent's prompt is:

> Read and follow `.claude/skills/qa-tv-retest-from-report/verify-agent.md` exactly. Work folder: `work/_golive-<name>`. Your page slugs: …

Each agent writes `<slug>/verdict.json` (`[{id, verdict, fixed_langs, still_langs, now}]`) and returns one line per page.

Spot-check before trusting the results:
- Any page reported 100% fixed while some locales 404: the 404 locales must be exactly the Source 404 issue's locales.
- One large page: compare a few `now` notes with the `.txt` snapshot.

## 4. Build and publish the new tracker

1. `python3 .claude/skills/qa-artifact-from-findings/tracker/upgrade.py SP/old.html artifact-<name>-golive/index.html --title "<Name> go-live" --heading "<Name>: go-live re-check on www"`
2. Edit the `intro` (and `built`) in the page's `<script id="data">` JSON. Say it is the go-live re-check against www on `<date>`, in all 17 locales.
3. Load `artifact-design` and `artifact-capabilities`, then publish as a NEW artifact:
   - `capabilities: {"db": {}, "user": {"scopes": ["profile"]}}`, `icon: "checklist"`.
   - Copy the screenshots server side through `files`: `{"shots/...": {"artifact": "<old url>", "path": "shots/..."}}`.
   - A publish takes at most 255 files including index.html. Republish the same file path with the rest; files you leave out are kept.

## 5. Write the statuses

1. Run `python3 K/statuses.py SP/old_data.json SP "<d Mon yyyy>" work/_golive-<name> --open-src SP/old.html`. It checks that every old id has exactly one verdict and builds one doc per issue. Each doc is `issues/<slug>_<id>` with `updatedAt` = now and `by: null`:

   | Verdict | status | flag |
   |---|---|---|
   | fixed | Fixed | "Verified fixed on www (go-live re-check <date>)" |
   | partly | Open | "Fixed in <locales>; still on www in <locales> (<date>)" |
   | still | Open | "Still on www at go-live re-check <date>: <now>" |
   | cant_check | Open | "Not re-checked: <reason>" |

2. Write them with `ArtifactData` `batch`, at most **50 writes per batch**.
   - For non-fixed docs, use `file_path: SP/db/<doc_id>.json`.
   - The fixed docs are identical, so inline `data` is shorter.
3. Check with one `query` on `status == "Open"`. It must return exactly the non-fixed issues.

## 6. Open-issues-only artifact (when asked)

`statuses.py --open-src` already wrote `SP/open_src.html`. It keeps only the non-fixed issues, narrows each issue's locales to the still-failing ones, appends what www shows now, and drops shared groups with fewer than two open members.

1. Run `upgrade.py SP/open_src.html artifact-<name>-open/index.html --title "<Name> open on www"`.
2. Edit the intro the same way.
3. Publish as a new artifact with the same capabilities. Copy over only those issues' screenshots.
4. Batch-write the open docs (`SP/db/<doc_id>.json`).

## 7. Report

Tell the user:
- the counts (fixed / partly / still / couldn't check);
- each open issue, with its locales;
- the pages that are fully clean now;
- the locales that failed to load, keeping intended 404s separate;
- the new artifact link(s), and that they're private until shared from the page's Share menu.
