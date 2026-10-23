// Run by browse.py / batch.py on each page. Builds a compact snapshot of the
// page body (header/footer excluded) anchored on h1/h2 headings, so it works
// even when UAT and live use completely different DOMs (e.g. AEM vs headless).
// Every tab is clicked and every accordion item expanded in turn so their
// hidden content is captured too; the page is put back in its load state
// afterwards (for the screenshot).
// window.__cmpData is the structured snapshot (used by diff.py) and
// window.__cmpOut the same as readable lines; the call returns its length.
await (async () => {
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const px = (v) => Math.round(parseFloat(v) || 0);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const hex = (c) => { const m = String(c || '').match(/rgba?\(([^)]+)\)/); if (!m) return c || '-'; const [r, g, b, a = 1] = m[1].split(/[\s,/]+/).filter(Boolean).map(Number); if (a === 0) return 'none'; const h = [r, g, b].map((n) => n.toString(16).padStart(2, '0')).join('').toUpperCase(); return a < 1 ? `#${h}@${Math.round(a * 100)}` : `#${h}`; };
  const step = Math.max(300, innerHeight * 0.8);
  for (let i = 0; i < 100; i++) { const y = scrollY; scrollBy(0, step); await sleep(120); if (scrollY === y) break; }
  scrollTo(0, 0); await sleep(500);
  const O = window.__CMP_OPTS || {};
  const ex = [...document.querySelectorAll('header,footer,[role=banner],[role=contentinfo],#header,#footer,nav,#onetrust-consent-sdk,#CybotCookiebotDialog' + (O.exclude ? ',' + O.exclude.join(',') : ''))]
    .filter((el) => !(el.parentElement && el.parentElement.closest('main article,[role=main] article')));
  const isEx = (el) => ex.some((x) => x === el || x.contains(el));
  const shown = (el) => { const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') return false; const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const W = document.documentElement.clientWidth;
  const anchors = [...document.querySelectorAll(O.anchors || 'h1,h2')].filter((h) => !isEx(h) && shown(h) && norm(h.innerText));
  const blockOf = (h) => { let b = h; while (b.parentElement && b.parentElement !== document.body && !anchors.some((o) => o !== h && b.parentElement.contains(o)) && !isEx(b.parentElement)) b = b.parentElement; return b; };
  const ctaSel = 'button,[role=button],a.btn,a.button,a[class*=btn],a[class*=cta],a[class*=button],a[class*=Button]';
  const centred = (el) => { const range = document.createRange(); range.selectNodeContents(el); const t = range.getBoundingClientRect(); const mid = t.left + t.width / 2; return Math.abs(mid - W / 2) <= 16 ? 'C' : (t.left < W / 2 ? 'L' : 'R'); };
  // Text colours, CTAs, images and text of whatever is visible inside root.
  const detail = (root, cap) => {
    const d = { texts: [], ctas: [], imgs: [], txt: norm(root.innerText).slice(0, cap) };
    const seen = new Set();
    [...root.querySelectorAll('p,li,span,div,h3,h4,h5,h6')].filter((e) => shown(e) && !isEx(e) && !e.closest(ctaSel) && [...e.childNodes].some((n) => n.nodeType === 3 && norm(n.textContent))).forEach((e) => {
      const es = getComputedStyle(e); const k = `${e.tagName} ${hex(es.color)} ${centred(e)}`;
      if (seen.has(k) || seen.size > 8) return; seen.add(k);
      d.texts.push({ tag: e.tagName, color: hex(es.color), align: centred(e), text: norm(e.innerText).slice(0, 40) });
    });
    [...root.querySelectorAll(ctaSel)].filter((e) => shown(e) && !isEx(e)).filter((e, _, a) => !a.some((o) => o !== e && o.contains(e))).slice(0, 10).forEach((e) => {
      const es = getComputedStyle(e); const er = e.getBoundingClientRect(); const af = getComputedStyle(e, '::after').content;
      d.ctas.push({ text: norm(e.innerText || e.getAttribute('aria-label')).slice(0, 40), color: hex(es.color), bg: hex(es.backgroundColor),
        border: es.borderTopStyle === 'none' || px(es.borderTopWidth) === 0 ? '0' : px(es.borderTopWidth) + hex(es.borderTopColor), r: px(es.borderTopLeftRadius),
        w: Math.round(er.width), h: Math.round(er.height), x: Math.round(er.left),
        icon: !!(e.querySelector('svg,img,i,[class*=icon]') || (af && af !== 'none' && af !== 'normal')),
        plain: hex(es.backgroundColor) === 'none' && (es.borderTopStyle === 'none' || px(es.borderTopWidth) === 0),
        href: (e.getAttribute('href') || '').replace(/^https?:\/\/[^/]+/, '').slice(0, 120) });
    });
    [...root.querySelectorAll('img')].filter((im) => shown(im) && !isEx(im)).slice(0, 12).forEach((im) => {
      const ir = im.getBoundingClientRect(); let f = im.currentSrc || im.src || ''; try { f = new URL(f).pathname.split('/').pop(); } catch (e) {}
      d.imgs.push({ file: f.slice(0, 60), w: Math.round(ir.width), h: Math.round(ir.height), x: Math.round(ir.left), broken: im.complete && im.naturalWidth === 0, alt: (im.alt || '').slice(0, 40) });
    });
    return d;
  };
  // A link to another page would navigate away mid-snapshot: never click one.
  const safe = (el) => { const a = el.closest('a[href]'); const h = a ? a.getAttribute('href') : '#'; return !h || h.startsWith('#') || /^javascript:/i.test(h); };
  const byId = (id) => (id ? document.getElementById(id) : null);
  const pairs = anchors.map((h) => ({ h, b: blockOf(h) }));
  const forms = [...document.querySelectorAll('form')].filter((f) => shown(f) && !isEx(f) && f.getBoundingClientRect().height > 100).length;
  const data = { url: location.href, lang: document.documentElement.lang, title: document.title.slice(0, 80),
    is404: /404|not found|nicht gefunden|introuvable|no encontrada|non trovata/i.test(document.title), vw: W, forms, blocks: [], headerCtas: [] };
  // Header: compare the navigation menu items (labels and order of each menu row, without
  // opening mega menus) and the styled CTA on the right of a menu row (e.g. "Book a demo").
  // Plain top-bar utility links on the right of the first row (contact sales, phone,
  // sign in) are out of scope.
  const hdrRoots = [...document.querySelectorAll('header,[role=banner],#header')].filter(shown);
  const styledOne = (e) => { const s = getComputedStyle(e); return hex(s.backgroundColor) !== 'none' || (s.borderTopStyle !== 'none' && px(s.borderTopWidth) > 0 && s.borderBottomStyle !== 'none'); };
  const styledEl = (e) => styledOne(e) || [...e.children].some((c) => shown(c) && styledOne(c) && c.getBoundingClientRect().width >= e.getBoundingClientRect().width - 4);
  const hdrEls = [...new Set(hdrRoots.flatMap((x) => [...x.querySelectorAll('a,button,[role=button]')]))]
    .filter((e) => shown(e) && e.getBoundingClientRect().top + scrollY < 260)
    .filter((e, _, a) => !a.some((o) => o !== e && o.contains(e)));
  // Main menu = the list holding the mega-menu triggers; top-bar utilities = the block
  // around the phone link (contact sales, phone, sign in); anything else is another
  // menu row (e.g. a section's own navigation).
  const upTo = (el, stop) => { let b = el; while (b.parentElement && !b.parentElement.contains(stop) && !hdrRoots.includes(b.parentElement)) b = b.parentElement; return b; };
  const trigger = hdrEls.find((e) => e.hasAttribute('aria-expanded') && e.getBoundingClientRect().left < W / 2 && norm(e.innerText));
  const tel = hdrEls.find((e) => /^tel:/i.test(e.getAttribute('href') || ''));
  const utilBox = tel ? (trigger ? upTo(tel, trigger) : tel.parentElement) : null;
  const mainBox = trigger ? (tel ? upTo(trigger, tel) : trigger.closest('ul,nav') || trigger.parentElement) : null;
  data.headerNav = [];
  const ctaEls = [], main = [], rows = [];
  hdrEls.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top || a.getBoundingClientRect().left - b.getBoundingClientRect().left).forEach((e) => {
    const r = e.getBoundingClientRect(); const text = norm(e.innerText);
    if (r.left >= W / 2 && styledEl(e) && text) { ctaEls.push(e); return; }
    if (!text || (utilBox && utilBox.contains(e))) return;
    if (e.querySelector('img,svg') && r.left < W / 8 && text.split(' ').length <= 3 && /home|teamviewer/i.test(text + (e.getAttribute('aria-label') || ''))) return; // the logo
    if (mainBox && mainBox.contains(e)) { main.push([r.left, text]); return; }
    let row = rows.find((x) => Math.abs(x.y - (r.top + r.height / 2)) < 24);
    if (!row) rows.push(row = { y: r.top + r.height / 2, items: [] });
    row.items.push([r.left, text]);
  });
  const lab = (a) => a.sort((x, y) => x[0] - y[0]).map((x) => x[1].slice(0, 40));
  if (main.length) data.headerNav.push({ row: 'main menu', items: lab(main) });
  rows.forEach((x, i) => data.headerNav.push({ row: main.length ? `second row${i ? ' ' + (i + 1) : ''}` : `row ${i + 1}`, items: lab(x.items) }));
  ctaEls.slice(0, 6).forEach((e) => {
    const es = getComputedStyle(e); const er = e.getBoundingClientRect();
    data.headerCtas.push({ text: norm(e.innerText || e.getAttribute('aria-label')).slice(0, 40), color: hex(es.color), bg: hex(es.backgroundColor),
      border: es.borderTopStyle === 'none' || px(es.borderTopWidth) === 0 ? '0' : px(es.borderTopWidth) + hex(es.borderTopColor), r: px(es.borderTopLeftRadius),
      w: Math.round(er.width), h: Math.round(er.height), x: Math.round(er.left), y: Math.round(er.top + scrollY),
      plain: false, target: e.getAttribute('target') || '_self',
      href: (e.getAttribute('href') || '').replace(/^https?:\/\/[^/]+/, '').slice(0, 120) });
  });
  pairs.forEach(({ h, b }, i) => {
    const r = b.getBoundingClientRect(); const cs = getComputedStyle(b); const hs = getComputedStyle(h);
    const next = pairs[i + 1]; const gap = next ? Math.round(next.b.getBoundingClientRect().top - r.bottom) : null;
    let bg = hex(cs.backgroundColor), el = b;
    while (bg === 'none' && el.parentElement && el !== document.body) { el = el.parentElement; bg = hex(getComputedStyle(el).backgroundColor); if (el.getBoundingClientRect().height > r.height * 3) { bg = 'none'; break; } }
    const blk = { tag: h.tagName, head: norm(h.innerText).slice(0, 80), top: Math.round(r.top + scrollY), h: Math.round(r.height), gap, bg,
      bgimg: [b, ...b.querySelectorAll('*')].some((e) => /url\(/.test(getComputedStyle(e).backgroundImage)),
      headColor: hex(hs.color), headAlign: centred(h), ...detail(b, 1500), tabs: [], acc: null, tabPanels: [], accItems: [] };
    blk.tabs = [...b.querySelectorAll('[role=tab]')].map((t) => (t.getAttribute('aria-selected') === 'true' ? '*' : '') + norm(t.innerText).slice(0, 30));
    const acc = [...b.querySelectorAll('[aria-expanded]')].filter(shown);
    if (acc.length) blk.acc = { open: acc.filter((a) => a.getAttribute('aria-expanded') === 'true').length, total: acc.length };
    data.blocks.push(blk);
  });

  // Tabs: click each one, snapshot its panel, then go back to the tab open on load.
  let budget = 120;  // clicks per page, so a huge FAQ can't stall the capture
  for (const [i, { b }] of pairs.entries()) {
    const blk = data.blocks[i];
    const tabs = [...b.querySelectorAll('[role=tab]')].filter((t) => shown(t) && !isEx(t)).slice(0, 12);
    if (!tabs.length) continue;
    const first = tabs.find((t) => t.getAttribute('aria-selected') === 'true');
    for (const t of tabs) {
      const tab = norm(t.innerText || t.getAttribute('aria-label')).slice(0, 40);
      if (!safe(t) || budget-- <= 0) { blk.tabPanels.push({ tab, skipped: safe(t) ? 'click limit' : 'tab is a link', texts: [], ctas: [], imgs: [], txt: '' }); continue; }
      t.scrollIntoView({ block: 'center' }); t.click(); await sleep(500);
      const own = byId(t.getAttribute('aria-controls'));
      const panel = (own && shown(own) && own) || [...b.querySelectorAll('[role=tabpanel]')].find(shown) || b;
      blk.tabPanels.push({ tab, selected: t.getAttribute('aria-selected') === 'true', whole: panel === b, url: location.search + location.hash, ...detail(panel, 1000) });
    }
    if (first && safe(first)) { first.click(); await sleep(300); }
  }

  // Accordions: expand each closed item, snapshot what opened, then close it again.
  const skipAcc = '[role=tab],[role=tablist] *,[aria-haspopup],[class*=carousel] *,[class*=slider] *,[class*=swiper] *,[class*=dropdown] *';
  for (const [i, { b }] of pairs.entries()) {
    const blk = data.blocks[i];
    const triggers = [...b.querySelectorAll('[aria-expanded], details > summary')]
      .filter((e) => shown(e) && !isEx(e) && !e.matches(skipAcc)).slice(0, 30);
    for (const t of triggers) {
      const det = t.tagName === 'SUMMARY' ? t.parentElement : null;
      const isOpen = () => (det ? det.open : t.getAttribute('aria-expanded') === 'true');
      const title = norm(t.innerText || t.getAttribute('aria-label')).slice(0, 60);
      const wasOpen = isOpen();
      if (!wasOpen) {
        if (!safe(t) || budget-- <= 0) { blk.accItems.push({ title, open: false, skipped: safe(t) ? 'click limit' : 'trigger is a link', texts: [], ctas: [], imgs: [], txt: '' }); continue; }
        t.scrollIntoView({ block: 'center' });
        if (det) det.open = true; else t.click();
        await sleep(450);
      }
      const own = byId(t.getAttribute('aria-controls'));
      const after = t.nextElementSibling || (t.parentElement !== b && t.parentElement.nextElementSibling);
      const panel = det || (own && shown(own) && own) || (after && shown(after) && after) || null;
      blk.accItems.push({ title, open: wasOpen, opened: isOpen(), url: location.search + location.hash, ...(panel ? detail(panel, 1000) : { texts: [], ctas: [], imgs: [], txt: '' }) });
      if (!wasOpen && isOpen()) { if (det) det.open = false; else t.click(); await sleep(250); }
    }
  }
  // Back to the top for the screenshot: instant (sites with smooth scrolling are
  // still moving otherwise) and with no focus ring left on the last clicked item.
  if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
  // <body> can be its own scroll area (overflow:auto), which scrollIntoView scrolls.
  scrollTo({ top: 0, left: 0, behavior: 'instant' }); document.body.scrollTop = 0; document.documentElement.scrollTop = 0; await sleep(500);

  const lines = [`URL ${data.url} | lang=${data.lang} | title=${data.title.slice(0, 60)} | 404=${data.is404} | vw=${W} | blocks=${data.blocks.length} | forms=${forms}`];
  data.headerCtas.forEach((c) => lines.push(`HEADER ${c.plain ? 'LINK' : 'CTA'} "${c.text}" ${c.color} on ${c.bg} border=${c.border} r=${c.r} ${c.w}x${c.h} x=${c.x} y=${c.y} -> ${c.href.slice(0, 60)}`));
  if (!data.headerCtas.length) lines.push('HEADER (no CTA in the header)');
  (data.headerNav || []).forEach((n) => lines.push(`HEADER NAV ${n.row}: ${n.items.join(' | ')}`));
  const content = (d, p) => {
    d.texts.forEach((t) => lines.push(`${p}T ${t.tag} ${t.color} ${t.align} "${t.text.slice(0, 30)}"`));
    d.ctas.forEach((c) => lines.push(`${p}CTA "${c.text.slice(0, 30)}" ${c.color} on ${c.bg} border=${c.border} r=${c.r} ${c.w}x${c.h} x=${c.x}${c.icon ? ' icon' : ''}${c.plain ? ' PLAIN' : ''} -> ${c.href.slice(0, 60)}`));
    d.imgs.forEach((m) => lines.push(`${p}IMG ${m.file.slice(0, 40)} ${m.w}x${m.h} x=${m.x}${m.broken ? ' BROKEN' : ''} alt="${m.alt.slice(0, 30)}"`));
  };
  data.blocks.forEach((k, i) => {
    lines.push(`\n#${i} ${k.tag} "${k.head.slice(0, 60)}" top=${k.top} h=${k.h} gapNext=${k.gap ?? '-'} bg=${k.bg}${k.bgimg ? ' bgimg' : ''} | head ${k.headColor} ${k.headAlign}`);
    content(k, ' ');
    if (k.tabs.length) lines.push(` TABS ${k.tabs.join(' / ')}`);
    if (k.acc) lines.push(` ACC open=${k.acc.open}/${k.acc.total}`);
    lines.push(` TXT ${k.txt.slice(0, 400)}`);
    k.tabPanels.forEach((t) => {
      lines.push(` TAB "${t.tab}"${t.url !== undefined ? ` url=${t.url || "(none)"}` : ""}${t.skipped ? ` (not clicked: ${t.skipped})` : t.selected === false ? ' (click did not select it)' : ''}${t.whole ? ' (no panel found: whole block)' : ''}`);
      content(t, '   · '); if (t.txt) lines.push(`   · TXT ${t.txt.slice(0, 400)}`);
    });
    k.accItems.forEach((a) => {
      lines.push(` ACCI "${a.title}"${a.url !== undefined ? ` url=${a.url || "(none)"}` : ""} ${a.open ? 'open on load' : 'closed on load'}${a.skipped ? ` (not opened: ${a.skipped})` : a.opened === false ? ' (did not open)' : ''}`);
      content(a, '   · '); if (a.txt) lines.push(`   · TXT ${a.txt.slice(0, 400)}`);
    });
  });
  window.__cmpData = data;
  window.__cmpOut = lines.join('\n');
  return window.__cmpOut.length;
})();
