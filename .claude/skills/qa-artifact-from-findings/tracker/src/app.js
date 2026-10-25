"use strict";
const D = JSON.parse(document.getElementById("data").textContent);
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const codes = D.locales.map((l) => l[0]), names = Object.fromEntries(D.locales);
const bySlug = Object.fromEntries(D.pages.map((p) => [p.slug, p]));

const SEVS = ["Blocker", "Major", "Minor"], SR = { Blocker: 0, Major: 1, Minor: 2 }, SW = [1000, 10, 1];
const STS = ["Open", "In progress", "Fixed", "Won't fix"], SC = { "Open": "open", "In progress": "prog", "Fixed": "fixed", "Won't fix": "wont" };
const RC = { new: "New at re-check", regressed: "Came back", fixed: "Gone at re-check" };
const key = (s, id) => s + "_" + id;
D.pages.forEach((p) => p.issues.forEach((i) => { i.slug = p.slug; i.key = key(p.slug, i.id); }));
const all = D.pages.flatMap((p) => p.issues);
const byKey = Object.fromEntries(all.map((i) => [i.key, i]));
const gOf = {};
D.shared.forEach((g) => g.refs.forEach(([s, id]) => { gOf[key(s, id)] = g.id; }));

// shared state, kept in the db capability
const T = { issues: {}, groups: {}, rechecks: {} };
const NM = {};
let db = null, me = { id: null, name: "" }, dis = " disabled", loaded = false;
const st = (o) => (o && o.status) || "Open";
const sevOf = (i) => (T.issues[i.key] && T.issues[i.key].sev) || i.sev;
const done = (s) => s === "Fixed" || s === "Won't fix";
const mineOf = (o) => !!o && ((me.id && o.ownerId === me.id) || (me.name && o.owner && String(o.owner).trim().toLowerCase() === me.name.toLowerCase()));
const isMine = (i) => mineOf(T.issues[i.key]) || (gOf[i.key] && mineOf(T.groups[gOf[i.key]]));
const fmt = (t) => { try { return new Date(t).toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); } catch (e) { return ""; } };
const cnt = (list) => { const c = { "Open": 0, "In progress": 0, "Fixed": 0, "Won't fix": 0 }; list.forEach((i) => { c[st(T.issues[i.key])]++; }); return c; };
const pct = (n, t) => t ? (100 * n / t).toFixed(1) : 0;
const bar = (c, n) => `<div class="bar" role="img" aria-label="${c.Fixed} of ${n} fixed"><i class="f" style="width:${pct(c.Fixed, n)}%"></i><i class="p" style="width:${pct(c["In progress"], n)}%"></i><i class="w" style="width:${pct(c["Won't fix"], n)}%"></i></div>`;

$("#heading").textContent = D.heading;
$("#intro").textContent = D.intro;
const langsHit = new Set(all.flatMap((i) => i.langs));
const ALWAYS_LISTED = ["Font Size"];  // shown in the type filter even when no issue has it yet
const kindsAll = D.type_order.filter((t) => ALWAYS_LISTED.includes(t) || all.some((i) => i.types.includes(t)));
const selKinds = new Set(kindsAll);
const issueOf = (s, id) => bySlug[s].issues.find((x) => x.id === id);
const cls = (n) => n === 0 ? "" : n === 1 ? "h1" : n <= 3 ? "h2" : n <= 6 ? "h3" : "h4";

// filters: type, status, severity, mine
function passState(i) {
  const fs = $("#fStatus").value, fv = $("#fSev").value, s = st(T.issues[i.key]);
  if (fs === "todo" ? done(s) : (fs && s !== fs)) return false;
  if (fv && sevOf(i) !== fv) return false;
  if ($("#fMine").checked && !isMine(i)) return false;
  return true;
}
const stateFiltered = () => !!($("#fStatus").value || $("#fSev").value || $("#fMine").checked);
const kindOn = (i) => i.types.some((t) => selKinds.has(t)) && passState(i);
const kindsFiltered = () => selKinds.size !== kindsAll.length || stateFiltered();

// the work strip under an issue or a shared group
function workHtml(coll, k, group, applyN) {
  const d = T[coll][k] || {}, s = st(d), i = group ? null : byKey[k];
  return `<div class="work" data-coll="${coll}" data-key="${esc(k)}">
    <select class="st" aria-label="Status"${dis}>${STS.map((x) => `<option${s === x ? " selected" : ""}>${esc(x)}</option>`).join("")}</select>
    ${group ? "" : `<select class="sv" aria-label="Severity"${dis}>${SEVS.map((x) => `<option${(d.sev || i.sev) === x ? " selected" : ""}>${x}</option>`).join("")}</select>`}
    <input type="text" class="ow" list="owners" placeholder="Assignee" aria-label="Assignee" value="${esc(d.owner || "")}"${dis}>
    <button type="button" class="me"${dis}>Assign to me</button>
    ${group ? `<button type="button" class="apply" data-gid="${esc(k)}"${dis}>Apply to all ${applyN} issues</button>` : ""}
    <textarea class="nt" rows="2" placeholder="Notes: what changed, ticket link, what is blocking" aria-label="Notes"${dis}>${esc(d.notes || "")}</textarea>
    <span class="by"></span></div>`;
}
function syncWork(w) {
  const coll = w.dataset.coll, k = w.dataset.key, d = T[coll][k] || {}, s = st(d);
  const set = (sel, v) => { const el = w.querySelector(sel); if (el && el !== document.activeElement && el.value !== v) el.value = v; };
  set(".st", s); set(".ow", d.owner || ""); set(".nt", d.notes || "");
  const art = w.closest(".issue");
  if (art) {
    const i = byKey[k], sev = d.sev || i.sev;
    set(".sv", sev);
    art.className = "issue s-" + SC[s];
    const chip = art.querySelector(".sev"); chip.className = "sev " + sev; chip.textContent = sev;
  }
  const by = w.querySelector(".by");
  by.textContent = [d.flag, d.updatedAt ? `Updated ${fmt(d.updatedAt)}${d.by ? " by " + (NM[d.by] || "a teammate") : ""}` : ""].filter(Boolean).join(" · ");
}

function renderProgress() {
  const n = all.length, c = cnt(all);
  const blk = all.filter((i) => sevOf(i) === "Blocker" && !done(st(T.issues[i.key]))).length;
  const wait = Object.values(T.rechecks).filter((d) => d && d.state === "requested").length;
  $("#progress").innerHTML = `${bar(c, n)}<div class="plabel"><span><b>${c.Fixed} of ${n}</b> fixed</span><span><b>${c["In progress"]}</b> in progress</span><span><b>${c["Won't fix"]}</b> won't fix</span><span><b>${c.Open}</b> open</span><span><b>${blk}</b> blockers not done</span>
    <button type="button" class="ghost" data-recheck="*"${dis} title="Asks whoever runs the QA skill to compare the pages again">${wait ? `Re-check requested for ${wait} page${wait === 1 ? "" : "s"}` : "Request re-check of all pages"}</button></div>`;
}
function rcFill(el) {
  const d = T.rechecks[el.dataset.slug];
  const req = d && d.state === "requested";
  el.innerHTML = `<button type="button" class="ghost" data-recheck="${esc(el.dataset.slug)}"${dis}${req ? " disabled" : ""}>${req ? "Re-check requested" : "Request re-check"}</button>`
    + (req ? `<span>Asked ${esc(fmt(d.updatedAt))}. It runs the next time someone runs the QA skill.</span>` : d && d.state === "done" ? `<span>Last re-checked ${esc(fmt(d.updatedAt))}${d.summary ? ": " + esc(d.summary) : ""}</span>` : "");
}

function renderSummary() {
  const kf = kindsFiltered();
  const pg = D.pages.map((p) => ({ p, is: p.issues.filter(kindOn) })).filter((x) => !kf || x.is.length);
  const vis = pg.flatMap((x) => x.is);
  const lh = new Set(vis.flatMap((i) => i.langs));
  const refsOf = (g) => g.refs.filter(([s, id]) => { const i = issueOf(s, id); return i && kindOn(i); });
  const sh = D.shared.map((g) => ({ g, refs: refsOf(g) })).filter((x) => x.refs.length);
  const openBlk = vis.filter((i) => sevOf(i) === "Blocker" && !done(st(T.issues[i.key]))).length;
  const messy = D.pages.filter((p) => p.messy && p.messy.on);
  $("#alarmPanel").hidden = !messy.length;
  $("#hAlarm").textContent = `${messy.length} messy page${messy.length === 1 ? "" : "s"}`;
  $("#alarmList").innerHTML = messy.map((p) => `<li><button data-go="${esc(p.slug)}">${esc(p.label)}</button>${p.messy.why.map((w) => `<span>${esc(w)}</span>`).join("")}</li>`).join("");
  $("#stats").innerHTML = [[vis.length, "issues"], [openBlk, "open blockers"], [messy.length, "messy pages", "bad"], [pg.length, "pages"], [lh.size + " / 17", "locales affected"], [sh.length, "fix-once groups"]]
    .map(([n, t, c]) => `<div class="stat ${c || ""}"><b>${n}</b><span>${t}</span></div>`).join("");
  renderProgress();
  let h = `<thead><tr><th></th>${codes.map((c) => `<th title="${esc(names[c])}">${c}</th>`).join("")}<th>All</th><th>Fixed</th></tr></thead><tbody>`;
  for (const { p, is } of pg) {
    h += `<tr><th class="row"><button data-go="${esc(p.slug)}">${esc(p.label)}</button>${p.messy && p.messy.on ? `<span class="messy-pill">Messy</span>` : ""}${p.note ? `<span class="note-pill" title="${esc(p.note)}">${esc(p.note_tag || "Note")}</span>` : ""}</th>`;
    for (const c of codes) {
      if (!p.checked.includes(c)) { h += `<td class="na" title="${esc(names[c])}: not checked"></td>`; continue; }
      const n = is.filter((i) => i.langs.includes(c) && i.rc !== "fixed").length;
      h += `<td class="${cls(n)}" title="${esc(p.label)}, ${esc(names[c])}: ${n} issue${n === 1 ? "" : "s"}">${n || "·"}</td>`;
    }
    const pc = cnt(p.issues);
    h += `<td class="tot">${is.filter((i) => i.rc !== "fixed").length}</td><td class="fx">${pc.Fixed}/${p.issues.length}${bar(pc, p.issues.length)}</td></tr>`;
  }
  $("#heat").innerHTML = h + "</tbody>";
  $("#sharedPanel").hidden = !sh.length;
  $("#sharedCount").textContent = `${sh.length} group${sh.length === 1 ? "" : "s"}`;
  if (document.activeElement && document.activeElement.closest && document.activeElement.closest("#shared")) return;
  sh.sort((a, b) => topSev(a.g) - topSev(b.g) || new Set(b.refs.map((r) => r[0])).size - new Set(a.refs.map((r) => r[0])).size);
  $("#shared").innerHTML = sh.map(({ g, refs }) => {
    const pages = [...new Set(refs.map((r) => r[0]))], top = SEVS[topSev(g)];
    const gc = cnt(g.refs.map(([s, id]) => issueOf(s, id)).filter(Boolean));
    return `<div class="row"><div class="count">${pages.length}<small>pages</small></div>
    <div style="min-width:0;display:grid;gap:6px"><h3>${esc(g.title)}</h3>
      <p class="fixline"><span class="fix">Fix in: ${esc(g.fix)}</span>${esc(g.note)}</p>
      <div class="refs">${refs.map(([s, id]) => `<button data-go="${esc(s)}" data-id="${id}">${esc(bySlug[s].label)} #${id}</button>`).join(" · ")}</div>
      <span class="gp">${gc.Fixed} of ${g.refs.length} issues fixed</span></div>
    <div class="chips"><span class="sev ${top}">${top}</span>${g.types.map((t) => `<span class="kind${t === "UI" || t === "Font Colour" || t === "Font Size" ? " ui" : ""}">${esc(t)}</span>`).join("")}</div>
    ${workHtml("groups", g.id, true, g.refs.length)}</div>`;
  }).join("");
  $("#shared").querySelectorAll(".work").forEach(syncWork);
}
function topSev(g) { return Math.min(...g.refs.map(([s, id]) => { const i = issueOf(s, id); return i ? SR[sevOf(i)] : 2; })); }
if (D.heat_note) $("#heatNote").textContent = D.heat_note; else $("#heatNote").hidden = true;

// issue-type multi-select
const kCount = Object.fromEntries(kindsAll.map((k) => [k, all.filter((i) => i.types.includes(k)).length]));
$("#kList").innerHTML = kindsAll.map((k) => `<label><input type="checkbox" value="${esc(k)}" checked>${esc(k)}<small>${kCount[k]}</small></label>`).join("");
function syncKinds() {
  for (const cb of document.querySelectorAll("#kList input")) cb.checked = selKinds.has(cb.value);
  $("#kindSum").textContent = selKinds.size === kindsAll.length ? "All issue types" : selKinds.size === 0 ? "No types selected" : selKinds.size === 1 ? [...selKinds][0] : `${selKinds.size} types selected`;
}
function setKinds(on) { selKinds.clear(); if (on) kindsAll.forEach((k) => selKinds.add(k)); syncKinds(); }
$("#kList").onchange = (e) => { e.target.checked ? selKinds.add(e.target.value) : selKinds.delete(e.target.value); syncKinds(); render(); };
$("#kAll").onclick = () => { setKinds(true); render(); };
$("#kNone").onclick = () => { setKinds(false); render(); };
document.addEventListener("click", (e) => { const dd = $("#kindDD"); if (dd.open && !dd.contains(e.target)) dd.open = false; });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("#kindDD").open = false; });

// filter controls
const opt = (v, t) => `<option value="${esc(v)}">${esc(t)}</option>`;
$("#fPage").innerHTML = opt("", "All pages") + D.pages.map((p) => opt(p.slug, p.label)).join("");
$("#fLang").innerHTML = opt("", "All locales") + D.locales.filter(([c]) => langsHit.has(c)).map(([c, n]) => opt(c, `${c} · ${n}`)).join("");
$("#fStatus").innerHTML = opt("", "All statuses") + opt("todo", "Not done (open + in progress)") + STS.map((s) => opt(s, s)).join("");
$("#fSev").innerHTML = opt("", "All severities") + SEVS.map((s) => opt(s, s)).join("");
$("#fSort").innerHTML = opt("sev", "Sort: severity first") + opt("orig", "Sort: original order");
const FILTERS = ["fPage", "fLang", "fStatus", "fSev", "fSort"];
try {
  const s = JSON.parse(localStorage.getItem("qa-filters") || "{}");
  for (const k of FILTERS) if (s[k] && [...$("#" + k).options].some((o) => o.value === s[k])) $("#" + k).value = s[k];
  $("#fMine").checked = !!s.mine;
  // A type that did not exist when the filter was saved starts selected; saves without `known` predate this and are ignored.
  if (Array.isArray(s.kinds) && Array.isArray(s.known)) { selKinds.clear(); kindsAll.forEach((k) => (s.kinds.includes(k) || !s.known.includes(k)) && selKinds.add(k)); }
} catch (e) {}
syncKinds();

const SEG = { CN: "cn", TW: "tw" };
const localeUrl = (url, c) => url.replace(/^(https?:\/\/[^/]+)\/[a-z]{2}(?=\/|$)/i, `$1/${SEG[c] || c.toLowerCase()}`);
function issueHtml(p, i) {
  const shot = (side, label) => i.shots[side] ? `<figure><figcaption style="color:var(--${side})">${label}</figcaption><img${D.packs ? "" : ` loading="lazy" src="${esc(i.shots[side])}"`} data-p="${esc(p.slug)}" data-s="${esc(i.shots[side])}" alt="${label} screenshot for issue ${i.id}"></figure>` : "";
  const shots = shot("uat", "UAT") + shot("live", "Live");
  const d = T.issues[i.key], sev = (d && d.sev) || i.sev;
  return `<article class="issue s-${SC[st(d)]}" id="${esc(p.slug)}-${i.id}"><span class="num">#${i.id}</span><div class="body">
    <div class="meta">${i.messy ? `<span class="messy-pill tag">Messy</span>` : ""}${i.quick ? `<span class="quick" title="Live has no such page, so removing it from UAT clears this issue">Quick fix: ${esc(i.quick)}</span>` : ""}<span class="sev ${sev}">${sev}</span>${RC[i.rc] ? `<span class="rcc ${i.rc}">${RC[i.rc]}</span>` : ""}${i.types.map((t) => `<span class="kind${t === "UI" || t === "Font Colour" || t === "Font Size" ? " ui" : ""}">${esc(t)}</span>`).join("")}<span>${esc(i.component)}</span></div>
    <h3>${esc(i.issue)}</h3>
    <div class="vals"><div><span class="k u">UAT</span>${esc(i.uat)}</div><div><span class="k l">Live</span>${esc(i.live)}</div></div>
    <div class="langs">${codes.filter((c) => p.checked.includes(c)).map((c) => i.langs.includes(c)
      ? `<a class="lang on" href="${esc(localeUrl(p.uat, c))}" target="_blank" rel="noopener" title="${esc(names[c])}: open UAT page">${c}</a>`
      : `<span class="lang off" aria-disabled="true" title="${esc(names[c])}: no issue">${c}</span>`).join("")}</div>
    ${i.cause ? `<p class="cause">Likely cause: ${esc(i.cause)}</p>` : ""}
    ${i.also.length ? `<p class="also">Also on ${i.also.map((s) => `<button data-go="${esc(s)}">${esc(bySlug[s].label)}</button>`).join(", ")}</p>` : ""}
    ${workHtml("issues", i.key, false)}
    ${shots ? `<div class="shots">${shots}</div>` : `<p class="noshot">No screenshot for this issue.</p>`}
  </div></article>`;
}
function render() {
  const fp = $("#fPage").value, fl = $("#fLang").value, ft = $("#fText").value.trim().toLowerCase(), bySev = $("#fSort").value !== "orig";
  try { localStorage.setItem("qa-filters", JSON.stringify({ fPage: fp, fLang: fl, fStatus: $("#fStatus").value, fSev: $("#fSev").value, fSort: $("#fSort").value, mine: $("#fMine").checked, kinds: [...selKinds], known: kindsAll })); } catch (e) {}
  let shown = 0; const blocks = [];
  for (const p of D.pages) {
    if (fp && p.slug !== fp) continue;
    const list = p.issues.filter((i) => (!fl || i.langs.includes(fl)) && kindOn(i)
      && (!ft || [i.issue, i.component, i.uat, i.live, i.cause].join(" ").toLowerCase().includes(ft)));
    shown += list.length;
    // A page with a note (e.g. redirects on both sides) has nothing to filter, so only the search hides it.
    if (!list.length && (ft || (!p.note && (fl || kindsFiltered())))) continue;
    list.sort((a, b) => (b.messy ? 1 : 0) - (a.messy ? 1 : 0) || (bySev ? SR[sevOf(a)] - SR[sevOf(b)] : 0) || a.id - b.id);
    const w = list.reduce((n, i) => n + (done(st(T.issues[i.key])) ? 0 : SW[SR[sevOf(i)]]), 0);
    const pc = cnt(p.issues);
    blocks.push({ w, m: p.messy && p.messy.on ? 1 : 0, html: `<section class="page" id="${esc(p.slug)}"><div class="page-head"><span class="eyebrow">${p.issues.length} issue${p.issues.length === 1 ? "" : "s"} · ${pc.Fixed} fixed · ${p.checked.length} locale${p.checked.length === 1 ? "" : "s"} checked${p.updated ? " · " + esc(p.updated) : ""}</span>
      <h2>${esc(p.label)}${p.messy && p.messy.on ? `<span class="messy-pill">Messy</span>` : ""}</h2>${p.messy && p.messy.on ? `<div class="alarm" role="alert"><b>Messy page</b>${p.messy.why.map((w) => `<span>${esc(w)}</span>`).join("")}</div>` : ""}${p.label !== p.title ? `<p class="note">${esc(p.title)}</p>` : ""}${p.note ? `<p class="note">${esc(p.note)}</p>` : ""}
      <div class="urls"><span><span class="u">UAT</span> <a href="${esc(p.uat)}" target="_blank" rel="noopener">${esc(p.uat)}</a></span><span><span class="l">Live</span> <a href="${esc(p.live)}" target="_blank" rel="noopener">${esc(p.live)}</a></span></div>
      <div class="rc" data-slug="${esc(p.slug)}"></div></div>
      ${list.map((i) => issueHtml(p, i)).join("") || (p.note && !p.issues.length ? `<p class="empty"><span class="note-pill tag">${esc(p.note_tag || "Note")}</span> Nothing to compare on this page.</p>` : `<p class="empty">No issues found on this page.</p>`)}
      ${p.not_issues.length ? `<details><summary>Possibly not an issue (${p.not_issues.length})</summary><ul>${p.not_issues.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></details>` : ""}
      ${p.couldnt_check.length ? `<details><summary>Couldn't check (${p.couldnt_check.length})</summary><ul>${p.couldnt_check.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></details>` : ""}
    </section>` });
  }
  blocks.sort((a, b) => b.m - a.m || (bySev ? b.w - a.w : 0));
  $("#pages").innerHTML = blocks.map((b) => b.html).join("") || `<p class="empty">No issues match these filters.</p>`;
  $("#pages").querySelectorAll(".work").forEach(syncWork);
  $("#pages").querySelectorAll(".rc").forEach(rcFill);
  renderSummary();
  fillOwners();
  $("#shown").textContent = `${shown} of ${all.length} issues`;
  if (D.packs) watchShots();
}
function fillOwners() {
  const o = new Set(); for (const c of [T.issues, T.groups]) for (const d of Object.values(c)) if (d && d.owner) o.add(d.owner);
  if (me.name) o.add(me.name);
  $("#owners").innerHTML = [...o].sort().map((n) => `<option value="${esc(n)}">`).join("");
}
// shared-state changes patch the page in place, so nothing a person is typing is lost
function patch() {
  document.querySelectorAll(".work").forEach(syncWork);
  document.querySelectorAll(".rc").forEach(rcFill);
  renderSummary(); fillOwners();
}
let patchT = 0;
const patchSoon = () => { cancelAnimationFrame(patchT); patchT = requestAnimationFrame(patch); };
document.addEventListener("focusout", () => setTimeout(() => { if (!document.activeElement || !document.activeElement.closest(".work")) patchSoon(); }, 0));

let toastT = 0;
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => { t.hidden = true; }, 3500); }

const chain = {};
function save(coll, k, patchBody) {
  if (!db) { toast("Changes can't be saved in this view."); return; }
  const cur = T[coll][k];
  if (cur && Object.keys(patchBody).every((f) => (cur[f] ?? null) === (patchBody[f] ?? null))) return;
  const body = { ...patchBody, updatedAt: new Date().toISOString(), by: me.id || null };
  T[coll][k] = { ...(cur || {}), ...body };
  const ref = db.collection(coll).doc(k), had = !!cur;
  chain[coll + k] = (chain[coll + k] || Promise.resolve())
    .then(() => had ? ref.update(body) : ref.set(T[coll][k]))
    .catch(async () => { try { await ref.set(T[coll][k]); } catch (e) { toast("Couldn't save that change. " + ((e && e.message) || "Try again.")); } });
  patchSoon();
}
const noteT = {};
document.addEventListener("input", (e) => {
  if (!e.target.matches(".nt")) return;
  const w = e.target.closest(".work"), id = w.dataset.coll + w.dataset.key, v = e.target.value;
  clearTimeout(noteT[id]); noteT[id] = setTimeout(() => save(w.dataset.coll, w.dataset.key, { notes: v }), 800);
});
document.addEventListener("change", (e) => {
  const w = e.target.closest(".work"); if (!w) return;
  const coll = w.dataset.coll, k = w.dataset.key, t = e.target;
  if (t.matches(".st")) save(coll, k, { status: t.value });
  else if (t.matches(".sv")) save(coll, k, { sev: t.value });
  else if (t.matches(".ow")) { const v = t.value.trim(); save(coll, k, { owner: v, ownerId: v && me.name && v.toLowerCase() === me.name.toLowerCase() ? me.id : null }); }
  else if (t.matches(".nt")) { clearTimeout(noteT[coll + k]); save(coll, k, { notes: t.value }); }
});
function applyGroup(gid) {
  const g = D.shared.find((x) => x.id === gid), d = T.groups[gid] || {};
  for (const [s, id] of g.refs) {
    const b = { status: st(d) };
    if (d.owner) { b.owner = d.owner; b.ownerId = d.ownerId || null; }
    save("issues", key(s, id), b);
  }
  toast(`Applied ${st(d)}${d.owner ? " and " + d.owner : ""} to ${g.refs.length} issues.`);
}

for (const id of ["fPage", "fLang", "fStatus", "fSev", "fSort", "fMine"]) $("#" + id).onchange = render;
$("#fText").oninput = render;
render();

document.addEventListener("click", (e) => {
  const rc = e.target.closest("[data-recheck]");
  if (rc) {
    const slugs = rc.dataset.recheck === "*" ? D.pages.map((p) => p.slug) : [rc.dataset.recheck];
    slugs.forEach((s) => save("rechecks", s, { state: "requested" }));
    toast(slugs.length > 1 ? "Re-check requested for all pages." : "Re-check requested."); return;
  }
  const mine = e.target.closest(".me");
  if (mine) { const w = mine.closest(".work"); save(w.dataset.coll, w.dataset.key, { owner: me.name || "Me", ownerId: me.id || null }); return; }
  const ap = e.target.closest(".apply");
  if (ap) { applyGroup(ap.dataset.gid); return; }
  const go = e.target.closest("[data-go]");
  if (go) {
    for (const id of ["fPage", "fLang", "fStatus", "fSev"]) $("#" + id).value = "";
    $("#fMine").checked = false; setKinds(true); $("#fText").value = ""; render();
    const el = document.getElementById(go.dataset.id ? `${go.dataset.go}-${go.dataset.id}` : go.dataset.go);
    if (el) el.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    return;
  }
  const img = e.target.closest(".shots img");
  if (img) { $("#lightbox img").src = img.src; $("#lightbox img").alt = img.alt; $("#lightbox").classList.add("open"); return; }
  if (e.target.closest("#lightbox")) $("#lightbox").classList.remove("open");
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("#lightbox").classList.remove("open"); });
$("#foot").textContent = `Built ${D.built} from the UAT vs live comparison reports. Status, assignee and notes are shared with everyone who opens this page.`;
if (location.hash) { const el = document.getElementById(location.hash.slice(1)); if (el) el.scrollIntoView(); }

// some artifacts ship screenshots packed, one text file per page (packs/<slug>.txt: 4-byte header length,
// JSON {path: [offset, length]}, then the image bytes, all base64). A screenshot whose own file is missing falls back to its pack.
const packs = {};
function loadPack(slug) {
  if (!packs[slug]) packs[slug] = fetch("packs/" + encodeURIComponent(slug) + ".txt").then((r) => { if (!r.ok) throw new Error(r.status); return r.text(); }).then((txt) => {
    const bin = atob(txt), buf = new Uint8Array(bin.length).buffer, u8 = new Uint8Array(buf); for (let k = 0; k < bin.length; k++) u8[k] = bin.charCodeAt(k);
    const n = new DataView(buf).getUint32(0), idx = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, n))), out = {};
    for (const [k, [o, l]] of Object.entries(idx)) out[k] = URL.createObjectURL(new Blob([buf.slice(4 + n + o, 4 + n + o + l)], { type: "image/jpeg" }));
    return out;
  });
  return packs[slug];
}
// packed artifacts (D.packs): load a page's pack when its first screenshot nears the viewport
function showShot(im) { loadPack(im.dataset.p).then((m) => { im.src = m[im.dataset.s] || im.dataset.s; }).catch(() => { im.src = im.dataset.s; }); }
function watchShots() {
  const pending = document.querySelectorAll("img[data-p]:not([src])");
  if (!("IntersectionObserver" in window)) { pending.forEach(showShot); return; }
  window.shotObs = window.shotObs || new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { window.shotObs.unobserve(e.target); showShot(e.target); } }), { rootMargin: "800px 0px" });
  pending.forEach((im) => window.shotObs.observe(im));
}
document.addEventListener("error", (e) => {
  const im = e.target;
  if (!im || im.tagName !== "IMG" || !im.dataset.p || im.dataset.tried) return;
  im.dataset.tried = "1";
  loadPack(im.dataset.p).then((m) => { if (m[im.dataset.s]) im.src = m[im.dataset.s]; else im.alt += " (could not load)"; }).catch(() => { im.alt += " (could not load)"; });
}, true);

// connect to the shared store; the page works read-only without it
const use = async (n) => { try { return window.claude && window.claude.use ? await window.claude.use(n) : null; } catch (e) { return null; } };
async function resolveNames() {
  const user = await use("user"); if (!user) return;
  const ids = new Set(); for (const c of Object.values(T)) for (const d of Object.values(c)) if (d && d.by) ids.add(d.by);
  if (!ids.size) return;
  try { const ps = await user.profiles([...ids]); for (const id of ids) NM[id] = (ps[id] && ps[id].name) || ""; } catch (e) { return; }
  document.querySelectorAll(".work").forEach(syncWork);
}
async function connect() {
  const note = (m) => { $("#dbNote").textContent = m; $("#dbNote").hidden = false; };
  let writable = true;
  const user = await use("user");
  if (user) {
    try { const v = await user.me(); me = { id: v.id || null, name: v.name || "" }; } catch (e) {}
    try { writable = (await user.can("data.write")) !== false; } catch (e) {}
  }
  db = await use("db");
  if (!db) { note("Status and notes can't be saved in this view. Open the page from your claude.ai account to track fixes."); dis = " disabled"; loaded = true; render(); return; }
  if (!writable) note("You have view-only access, so you can see status and notes but not change them.");
  dis = writable ? "" : " disabled";
  let first = 0;
  const arrived = () => { if (++first === 3 && !loaded) { loaded = true; render(); } };
  const flip = setTimeout(() => { if (!loaded) { loaded = true; render(); } }, 5000);
  for (const coll of ["issues", "groups", "rechecks"]) {
    let got = false;
    db.collection(coll).onSnapshot((snap) => {
      T[coll] = {}; snap.docs.forEach((d) => { T[coll][d.id] = d.data(); });
      if (!got) { got = true; arrived(); } else if (loaded) patchSoon();
      if (loaded && first >= 3) { patchSoon(); resolveNames(); }
    }, () => { if (!got) { got = true; arrived(); } note("Live updates stopped. Reload the page to reconnect."); });
  }
  clearTimeout(flip);
  setTimeout(() => { if (!loaded) { loaded = true; render(); } }, 5000);
  resolveNames();
}
connect();
