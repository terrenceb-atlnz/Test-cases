"""Build a self-contained interactive HTML review sheet (many-to-one capable).

Merges data/candidates.json with all data/decisions/dec_*.json (my reranks). Each MASTER
Manual Test Case (AWPTCM) can be matched to ONE OR MORE candidates from historical TestLink data (checkboxes), or NONE. Supports the project goal of mapping sources to Manual Cases for Objective synthesis.

Decision schema (dec_*.json): {"<KEY>": {"m": id | [ids] | null, "c": conf, "w": why}}

Usage: python3 build_review_html.py [out.html]
"""
import sys, json, glob

OUT = sys.argv[1] if len(sys.argv) > 1 else "review.html"
C = json.load(open("data/candidates.json"))
TL = {c["id"]: c for c in json.load(open("data/testlink_awp.json"))}
dec = {}
for f in sorted(glob.glob("data/decisions/dec_*.json")):
    dec.update(json.load(open(f)))


def as_list(m):
    if m is None:
        return []
    return m if isinstance(m, list) else [m]


cases, ref_ids = [], set()
for x in C:
    r = dec.get(x["key"])
    cands = [{"id": c["id"], "title": c["title"], "suite": c["suite"],
              "score": c["score"], "snip": c["snippet"]} for c in x["candidates"][:8]]
    ref_ids.update(c["id"] for c in cands)
    rec = as_list((r or {}).get("m"))
    ref_ids.update(rec)
    cases.append({
        "key": x["key"], "title": x["title"], "area": x["area"], "feature": x["feature"],
        "folder": x["folder"].replace("/New Platform Test (MASTER)", "") or "/",
        "self": x.get("self_snippet", ""),
        "rec": rec, "conf": (r or {}).get("c"), "why": (r or {}).get("w"),
        "decided": r is not None, "cands": cands,
    })

DETAIL = {}
for cid in ref_ids:
    c = TL.get(cid)
    if not c:
        continue
    DETAIL[cid] = {"summary": c.get("summary", ""), "pre": c.get("preconditions", ""),
                   "suite": c.get("suite"), "title": c.get("title"),
                   "steps": [{"a": s.get("action", ""), "e": s.get("expected", "")}
                             for s in c.get("steps", [])]}

DATA = json.dumps(cases, ensure_ascii=False)
DETAILJS = json.dumps(DETAIL, ensure_ascii=False)

PAGE = r"""<style>
:root{--bg:#0f1115;--card:#171a21;--mut:#8b95a7;--fg:#e7ecf3;--line:#262b36;
--acc:#3b82f6;--none:#f85149;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
header{position:sticky;top:0;z-index:5;background:#0f1115ee;backdrop-filter:blur(8px);
border-bottom:1px solid var(--line);padding:12px 18px}
h1{font-size:16px;margin:0 0 8px}
.stats{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--mut);margin-bottom:8px}
.stats b{color:var(--fg)}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
input,select,button{background:var(--card);color:var(--fg);border:1px solid var(--line);
border-radius:6px;padding:6px 9px;font-size:13px}
button{cursor:pointer}button.primary{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
main{max-width:1100px;margin:0 auto;padding:16px}
.case{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:0 0 14px}
.case.pending{opacity:.85;border-style:dashed}
.chead{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.ttl{font-weight:600}.meta{font-size:12px;color:var(--mut);margin-top:2px}
.badge{font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;white-space:nowrap}
.b-high{background:#1c3a24;color:#5ddc7a}.b-med{background:#3a3318;color:#e7c451}
.b-low{background:#2a2f3a;color:#9aa6b8}.b-pend{background:#2a2f3a;color:#9aa6b8}
.zself{font-size:12px;color:#b9c2d0;margin:8px 0;padding:7px 9px;background:#0f1218;border-radius:6px;border:1px solid var(--line)}
.why{font-size:12px;color:#e7c451;margin:6px 0}
.hint{font-size:11px;color:var(--mut);margin:2px 0 6px}
.cand{display:flex;gap:9px;align-items:flex-start;padding:7px;border-radius:7px;cursor:pointer;border:1px solid transparent}
.cand:hover{background:#0f1218}
.cand.sel{background:#13233f;border-color:var(--acc)}
.cand input{margin-top:3px}
.cid{font-family:ui-monospace,monospace;font-size:12px;color:var(--acc);min-width:78px}
.ctitle{font-weight:600;font-size:13px}
.csuite{font-size:11px;color:var(--mut)}
.cscore{font-size:11px;color:var(--mut);min-width:42px;text-align:right}
.csnip{font-size:12px;color:#9aa6b8}
.none{color:var(--none)}
.hidden{display:none}
.exp{margin-left:6px;font-size:11px;color:var(--mut);border:1px solid var(--line);
border-radius:5px;padding:1px 6px;background:#0f1218;cursor:pointer;white-space:nowrap}
.detail{margin:4px 0 8px 88px;padding:8px 10px;background:#0d1017;border:1px solid var(--line);
border-radius:6px;font-size:12px;color:#c2cbd8}
.detail .st{margin:4px 0;padding-left:8px;border-left:2px solid var(--line)}
.detail .ex{color:#8fd0a0}
</style>
<header>
<h1>MASTER Folder Enrichment &mdash; Match Review <span style="font-weight:400;color:#8b95a7;font-size:12px">(select one or more per case)</span></h1>
<div class="stats" id="stats"></div>
<div class="controls">
<input id="q" placeholder="search feature / candidate / id..." style="min-width:240px">
<select id="ffolder"></select>
<select id="fstatus">
<option value="">all</option><option value="decided">recommended</option>
<option value="pending">pending</option><option value="accepted">accepted</option>
<option value="changed">changed</option><option value="none">no-match</option>
<option value="multi">multi-match</option>
</select>
<select id="fconf"><option value="">any conf</option><option>high</option><option>med</option><option>low</option></select>
<button class="primary" id="export">Export decisions JSON</button>
<button id="copy">Copy JSON</button>
</div>
</header>
<main id="list"></main>
<script>
const DATA=__DATA__;
const DETAIL=__DETAIL__;
const state={}; // key -> {chosen:Set, touched:bool}
DATA.forEach(c=>{state[c.key]={chosen:new Set(c.rec),touched:false};});

const folders=[...new Set(DATA.map(c=>c.folder))].sort();
const ff=document.getElementById('ffolder');
ff.innerHTML='<option value="">all folders</option>'+folders.map(f=>`<option>${f}</option>`).join('');
function esc(s){return (s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}
function eq(set,arr){return set.size===arr.length && arr.every(x=>set.has(x));}

function statusOf(c){const s=state[c.key];
  if(!c.decided && !s.touched && s.chosen.size===0) return 'pending';
  if(s.chosen.size===0) return 'none';
  if(s.touched && !eq(s.chosen,c.rec)) return 'changed';
  return 'accepted';}

function render(){
  const q=document.getElementById('q').value.toLowerCase();
  const fF=ff.value, fS=document.getElementById('fstatus').value, fC=document.getElementById('fconf').value;
  const list=document.getElementById('list'); list.innerHTML=''; let shown=0;
  for(const c of DATA){
    if(fF&&c.folder!==fF)continue;
    if(fC&&c.conf!==fC)continue;
    const st=statusOf(c);
    if(fS==='multi'){if(state[c.key].chosen.size<2)continue;}
    else if(fS&&st!==fS)continue;
    if(q){const hay=(c.feature+' '+c.area+' '+c.key+' '+c.cands.map(x=>x.id+x.title).join(' ')).toLowerCase();
      if(!hay.includes(q))continue;}
    shown++;
    const div=document.createElement('div');
    div.className='case'+(st==='pending'?' pending':'');
    const badge=c.conf?`<span class="badge b-${c.conf}">${c.conf}</span>`:`<span class="badge b-pend">pending</span>`;
    const chosen=state[c.key].chosen;
    let cands=c.cands.map(cd=>{
      const sel=chosen.has(cd.id)?' sel':'';
      return `<label class="cand${sel}" data-k="${c.key}" data-id="${cd.id}">
        <input type="checkbox" ${chosen.has(cd.id)?'checked':''}>
        <span class="cid">${cd.id}</span>
        <span style="flex:1"><span class="ctitle">${esc(cd.title)}</span>
        <span class="csuite"> · ${esc(cd.suite)}</span>
        <button class="exp" data-exp="${cd.id}" data-host="${c.key}">full ▾</button>
        <br><span class="csnip">${esc(cd.snip)}</span></span>
        <span class="cscore">${cd.score.toFixed(2)}</span></label>
        <div class="detail hidden" id="d_${c.key}_${cd.id}"></div>`;
    }).join('');
    const noneSel=(chosen.size===0&&(c.decided||state[c.key].touched))?' sel':'';
    cands+=`<label class="cand${noneSel}" data-k="${c.key}" data-id="__none__">
      <input type="checkbox" ${chosen.size===0&&(c.decided||state[c.key].touched)?'checked':''}>
      <span class="cid none">NONE</span><span style="flex:1" class="none">No relevant TestLink match</span></label>`;
    const recTxt=c.rec.length?c.rec.join(', '):'NONE';
    div.innerHTML=`<div class="chead"><div><div class="ttl">${esc(c.feature)}</div>
      <div class="meta">${c.key} · ${esc(c.area)} · ${esc(c.folder)}</div></div>${badge}</div>
      ${c.self?`<div class="zself">ZEPHYR: ${esc(c.self)}</div>`:''}
      ${c.why?`<div class="why">★ recommend ${recTxt} — ${esc(c.why)}</div>`:''}
      <div class="hint">tick all TestLink cases whose content applies (many-to-one allowed)</div>
      ${cands}`;
    list.appendChild(div);
  }
  document.getElementById('stats').innerHTML=statsHTML(shown);
}
function statsHTML(shown){
  let acc=0,chg=0,non=0,pen=0,multi=0;
  DATA.forEach(c=>{const s=statusOf(c);acc+=s==='accepted';chg+=s==='changed';non+=s==='none';pen+=s==='pending';
    if(state[c.key].chosen.size>=2)multi++;});
  return `<span><b>${DATA.length}</b> cases</span><span>showing <b>${shown}</b></span>
    <span style="color:#5ddc7a">accepted <b>${acc}</b></span>
    <span style="color:#e7c451">changed <b>${chg}</b></span>
    <span style="color:#f85149">no-match <b>${non}</b></span>
    <span>pending <b>${pen}</b></span><span style="color:#7aa2f7">multi <b>${multi}</b></span>`;
}
document.getElementById('list').addEventListener('click',e=>{
  const exp=e.target.closest('.exp');
  if(exp){e.preventDefault();e.stopPropagation();
    const box=document.getElementById('d_'+exp.dataset.host+'_'+exp.dataset.exp);
    if(box.classList.contains('hidden')&&!box.dataset.f){
      const d=DETAIL[exp.dataset.exp];
      if(d){box.innerHTML=`<div><b>${exp.dataset.exp}</b> · ${esc(d.suite||'')}</div>`+
        (d.summary?`<div style="margin:4px 0">${esc(d.summary)}</div>`:'')+
        (d.pre?`<div style="margin:4px 0;color:#d29922">PRECOND: ${esc(d.pre)}</div>`:'')+
        d.steps.map((s,i)=>`<div class="st">${i+1}. ${esc(s.a)}${s.e?` <span class="ex">⇒ ${esc(s.e)}</span>`:''}</div>`).join('');
      }else{box.textContent='(no detail)';}
      box.dataset.f='1';}
    box.classList.toggle('hidden');return;}
  const lab=e.target.closest('.cand'); if(!lab)return;
  e.preventDefault();
  const k=lab.dataset.k, id=lab.dataset.id, s=state[k];
  if(id==='__none__'){s.chosen.clear();}
  else{if(s.chosen.has(id))s.chosen.delete(id);else s.chosen.add(id);}
  s.touched=true; render();
});
['q','ffolder','fstatus','fconf'].forEach(id=>document.getElementById(id).addEventListener('input',render));
function decisions(){const o={};DATA.forEach(c=>{const s=state[c.key];
  if(c.decided||s.touched)o[c.key]={matches:[...s.chosen],status:statusOf(c)};});return o;}
document.getElementById('export').addEventListener('click',()=>{
  const blob=new Blob([JSON.stringify({decisions:decisions()},null,1)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='decisions.json';a.click();
});
document.getElementById('copy').addEventListener('click',async()=>{
  await navigator.clipboard.writeText(JSON.stringify({decisions:decisions()},null,1));
  const b=document.getElementById('copy');b.textContent='Copied!';setTimeout(()=>b.textContent='Copy JSON',1200);
});
render();
</script>"""

open(OUT, "w").write(PAGE.replace("__DATA__", DATA).replace("__DETAIL__", DETAILJS))
print(f"wrote {OUT} ({len(cases)} cases, {len(dec)} decided, {len(DETAIL)} details)")
