Go-live re-check of an old UAT-vs-live QA log. Project folder: the uat-live-page-compare project root (run Python as `python3` on macOS, `py -3.13` on Windows).

Context: www.teamviewer.com now serves the new Sitecore build (formerly internal.teamviewer.com = "UAT"). The old QA log compared UAT against the OLD www ("live"). For each old issue, the old "uat" value is the FAULT and the old "live" value is the EXPECTED result. Decide whether the current www now matches the expected value.

For each page slug you are given (<WORK> is the work folder named in your prompt, e.g. work/_golive-usecases3):
- Read <WORK>/<slug>/old_issues.json (issues: id, component, kind, issue, uat, live, langs, ...; plus not_issues/couldnt_check for context).
- Current www snapshots, captured today at 1440px: <WORK>/<slug>/<CODE>-now.txt and <CODE>-now.json for all 17 codes (EN DE FR ES JA PT CN HU IT KO NL PL TH RU CS TW TR; RU was loaded from /ru-cis/). The first .txt line has the URL, title and 404=true/false; the .json has "status". The .txt lists HEADER CTA / HEADER NAV lines, then each block (#n heading, alignment L/C, colours, gapNext, bg, CTAs with colours/radius/size/href, IMG sizes, T P pretitles/eyebrows with colour, TAB lines with url=?tab=..., ACCI lines with the hash they set, TXT text). EN also has screenshot slices EN-now-NN.jpg (view with the Read tool when the text can't decide a visual question). Before trusting a .txt, make sure it doesn't contain "Error 1015" or "Too Many Requests" (none did at capture time).
- Check every issue in EVERY locale it lists in "langs".

Verdicts:
- fixed: www now matches the expected live value in every listed locale.
- partly: fixed in some listed locales only (fill fixed_langs and still_langs).
- still: www still shows the fault in all listed locales.
- cant_check: the locale didn't load, or the snapshot can't tell (hover, animation, carousel order, something not captured). Give the reason in "now".
Special rules:
- Source 404 issues (live returned 404 but UAT had content): fixed when www now returns 404 in those locales; still when it loads content.
- If a locale that the issue lists now returns 404 on www but the issue is NOT a Source 404 issue (e.g. missing component / untranslated content), the expected content is not there: count that locale as still (say "page 404 on www" in now).
- Header CTA issues: use the HEADER CTA line. Header nav label issues: use the HEADER NAV line.
- Accordion-hash issues: fixed if ACCI lines record a #hash being set (presence of a hash is enough; the hash value need not match). Tab-query issues: same with TAB url=?tab=... (presence only).
- Known not-issues (team accepts them; if an old issue is purely one of these, mark it fixed with now "accepted difference"): employee ranges, form arrow, hash/query exact values, navy titles, tab colours, header CTA design. Don't stretch this — only when the issue is purely that.
- You may use .claude/skills/uat-live-page-compare/scripts/browse.py at concurrency 1 (read its usage in the file) for anything the snapshots miss; keep it to a few loads.

Output for each page: write <WORK>/<slug>/verdict.json as a JSON list, one entry per old issue id, in id order:
[{"id": 1, "verdict": "fixed|partly|still|cant_check", "fixed_langs": [...], "still_langs": [...], "now": "<what www shows now, short, <= 120 chars>"}]
For fixed, fixed_langs = the listed langs and still_langs = []. For still, still_langs = the listed langs. For cant_check, put any locales that couldn't be checked in still_langs and explain in now.

Validate each file with python3 -c "import json;json.load(open(...))" and make sure every old issue id is present exactly once.

Final reply: one line per page: "<slug>: N issues — fixed X, partly Y, still Z, cant_check W; locales that failed to load: ..." and nothing else.
