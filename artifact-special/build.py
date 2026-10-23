import json, pathlib, re, shutil, datetime
W = pathlib.Path('.')
OUT = W/'artifact-special'
import sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

def sections_of(slug):
    n=0
    for side in ('live','uat'):
        try: n=max(n,len(re.findall(r'^#\d+',(W/'work'/slug/f'en-{side}.txt').read_text(encoding='utf8'),re.M)))
        except OSError: pass
    return n
pages=[]; grp={}
for slug in LABEL:
    f = json.load(open(W/'work'/slug/'findings.json',encoding='utf8'))
    plan = json.load(open(W/'work'/slug/'plan.json',encoding='utf8'))
    checked=[c for c,_ in LOC if c in plan['locales']]
    issues=[]
    for i in f['issues']+[dict(r,resolved=True) for r in f.get('resolved_issues',[])]:
        kind=norm_kind(i)
        g=GROUPS.get(i.get('signature'))
        if g and not i.get('resolved'): grp.setdefault(g,[]).append([slug,i['id']])
        for side in ('uat','live'):
            p=i.get('shots',{}).get(side)
            if p and not (W/'reports'/p).exists(): print('MISSING',p); i['shots'].pop(side)
        issues.append(dict(id=i['id'],component=i['component'],kind=kind,issue=i['issue'],uat=i['uat'],live=i['live'],cause=i.get('cause',''),
            sev=severity(kind,i.get('signature')),ui=is_ui(kind,i.get('signature')),quick=('Unpublish in Sitecore' if kind=='Source 404' or i.get('signature')=='faq-extra-locales' else ''),sig=i.get('signature',''),rc=('fixed' if i.get('resolved') else i.get('recheck','')),langs=[N2C[n] for n in i['languages'] if n in N2C],shots=i.get('shots',{}),group=g or '',also=[]))
    for x in issues: x['types']=types_of(x['kind'],x['ui'],x['issue']+' | '+x['uat'],x['component'],x['sig'])
    messy=messy_check(issues,sections_of(slug),bool(f.get('version_mismatch')))
    pages.append(dict(slug=slug,messy=messy,label=LABEL[slug],title=f['title'],uat=plan['uat'],live=plan['live'],checked=checked,issues=issues,
        not_issues=f['not_issues'],couldnt_check=f['couldnt_check'],updated=f.get("rechecked_on") or "22 October 2026"))
by={p['slug']:p for p in pages}
shared=[]
for g,refs in grp.items():
    if len({r[0] for r in refs})<2: continue
    shared.append(dict(id=g,title=GT[g][0],kind=GT[g][1],types=[t for t in TYPE_ORDER if any(t in x['types'] for s,i in refs for x in by[s]['issues'] if x['id']==i)],fix=FIX[g][0],note=FIX[g][1],refs=refs))
    for s,i in refs:
        iss=[x for x in by[s]['issues'] if x['id']==i][0]
        iss['also']=sorted({r[0] for r in refs if r[0]!=s})
shared.sort(key=lambda g:-len({r[0] for r in g['refs']}))
n=sum(len(p['issues']) for p in pages)
data=dict(type_order=TYPE_ORDER,locales=LOC,title="TeamViewer special pages QA log",heading="TeamViewer special pages: internal vs live",
 intro=f"{len(pages)} special pages on internal.teamviewer.com compared with www.teamviewer.com in all 17 locales at 1440px wide, header CTA and menu included, footer and top-bar utility links excluded; checked 22 October 2026. Source 404 means live (source) returns 404; Target 404 means the internal page (target) returns 404.",
 heat_note="Most issues sit in locales that live does not publish (HU, PL, TH, RU, CS, TW, TR) and in the German UAT pages, which repeat blocks many times or load empty.",
 built=datetime.date.today().strftime("%d %B %Y").lstrip("0"),pages=pages,shared=shared)
SRC = OUT/'src'
head = (SRC/'head.html').read_text(encoding='utf8'); app = (SRC/'app.js').read_text(encoding='utf8')
blob = json.dumps(data,ensure_ascii=False).replace('</','<\\/')
(OUT/'index.html').write_text(head+'\n<script type="application/json" id="data">'+blob+'</script>\n<script>\n'+app+'</script>\n',encoding='utf8')
files={}
for p in pages:
    for i in p['issues']:
        for v in i['shots'].values(): files[v]='reports/'+v
(OUT/'files.json').write_text(json.dumps(files),encoding='utf8')
print(n,'issues',len(files),'files',len(shared),'shared groups'); print({k:len(v) for k,v in grp.items()})
