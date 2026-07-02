#!/usr/bin/env python3
# Usage: python3 gather_suite.py <suiteId>  -> writes /tmp/logs_<suiteId>.json (+ prints summary to stderr)
import re,html,json,sys,urllib3,time
import requests
from concurrent.futures import ThreadPoolExecutor
urllib3.disable_warnings()
BASE="https://intranet.atlnz.lc/systest/ATPyLib/regression"
SID=sys.argv[1]
CUTOFF="2025-06-22"   # 12 months before 2026-06-22
tl=__import__('threading').local()
def sess():
    if not getattr(tl,'s',None): tl.s=requests.Session(); tl.s.verify=False
    return tl.s
def getp(url,maxbytes=300000):
    for _ in range(3):
        try:
            r=sess().get(url,timeout=60,stream=True); buf=b''
            for ch in r.iter_content(16384):
                buf+=ch
                if len(buf)>=maxbytes: break
            r.close(); return buf.decode('utf-8','replace')
        except Exception: time.sleep(1)
    return ''
def clean(x): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',x))).strip()
def crs(cell): return [i for i in re.findall(r'DisplayRecord\.php\?id=([^"&]+)"',cell) if i]
ROW=re.compile(r'test_suite_run\.php\?runNum=(\d+)">([^<]*)</a></td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*><span[^>]*>([^<]*)</span></td>\s*<td[^>]*><a href=logs\.php\?uid=(\d+)',re.S)

# 1) suite page -> case list + suite name + per-case suite-table fields
suite=getp(f"{BASE}/test_suite.php?testSuiteId={SID}")
m=re.search(r'<h2[^>]*>(\d+_[^<]+?)</h2>',suite) or re.search(r'All Test Cases \(\d+\) for ([^<]+)<',suite)
sname=(m.group(1).strip() if m else f"suite_{SID}")
seg=suite[suite.find('All Test Cases'):] if 'All Test Cases' in suite else ''
casemeta={}
for r in re.findall(r'<tr[^>]*>(.*?)</tr>',seg,re.S):
    cells=re.findall(r'<td[^>]*>(.*?)</td>',r,re.S)
    if not cells: continue
    mm=re.search(r'testSetId=(\d+)&testCaseId=(\d+)">([\d.]+)</a>',cells[0])
    if not mm: continue
    full=mm.group(3)
    casemeta[full]=dict(testSet=int(mm.group(1)),caseId=int(mm.group(2)),
        description=clean(cells[1]) if len(cells)>1 else '',
        reference=clean(cells[2]) if len(cells)>2 else '',
        past_crs=crs(cells[3]) if len(cells)>3 else [],
        current_crs=crs(cells[4]) if len(cells)>4 else [])

def work(item):
    full,meta=item
    page=getp(f"{BASE}/test_case.php?testSuiteId={SID}&testSetId={meta['testSet']}&testCaseId={meta['caseId']}")
    i=page.find('All Past Execution Results'); region=page[i:] if i>=0 else ''
    runs=[]
    for m in ROW.finditer(region):
        rn,plat,ver,bd,st,en,ex,res,uid=[g.strip() for g in m.groups()]
        runs.append(dict(runNum=rn,platform=plat,version=ver,ended=en,result=res.upper(),uid=uid))
    runs.sort(key=lambda r:r['ended'],reverse=True)
    sel=None; nrp=False
    if runs:
        if runs[0]['result']=='PASS': sel=runs[0]
        else:
            p=[r for r in runs if r['result']=='PASS' and r['ended']>=CUTOFF]
            if p: sel=p[0]
            else: sel=runs[0]; nrp=True
    logtext=''
    if sel:
        lp=getp(f"{BASE}/logs.php?uid={sel['uid']}")
        pres=re.findall(r'<pre[^>]*>(.*?)</pre>',lp,re.S|re.I)
        logtext=re.sub(r'\x1b\[[0-9;]*m','',html.unescape(re.sub(r'<[^>]+>','',"\n".join(pres)))).strip()
    return dict(test_id=full,**meta,run_count=len(runs),selected=sel,no_recent_pass=nrp,log_text=logtext)

res=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    for r in ex.map(work,list(casemeta.items())): res.append(r)
res.sort(key=lambda r:[int(x) for x in r['test_id'].split('.')])
out=dict(suite_id=SID,suite_name=sname,case_count=len(res),cases=res)
open(f"/tmp/logs_{SID}.json","w").write(json.dumps(out))
got=sum(1 for r in res if r['log_text'])
print(f"suite {SID} ({sname}): {len(res)} cases | with_log={got} | no_recent_pass={sum(1 for r in res if r['no_recent_pass'])} | no_runs={sum(1 for r in res if r['run_count']==0)}",file=sys.stderr)
