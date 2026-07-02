"""Local TF-IDF retrieval: top-K candidates (from TestLink/AWP data) per MASTER (Zephyr) Manual Test Case.

Part of the Test-cases project: helps identify relevant historical TestLink cases to synthesize Objectives for thin Manual Cases (AWPTCM-Txxxx) and support mappings.

Pure stdlib (no numpy/sklearn). No data leaves the machine. Self-contained output:
each candidate carries a content snippet so it can drive both rerank and the HTML sheet.

Usage: python3 build_candidates.py [zephyr_master.json] [testlink_awp.json] [out.json]
"""
import sys, json, re, math
from collections import defaultdict, Counter

ZIN = sys.argv[1] if len(sys.argv) > 1 else "data/zephyr_master.json"
TIN = sys.argv[2] if len(sys.argv) > 2 else "data/testlink_awp.json"
OUT = sys.argv[3] if len(sys.argv) > 3 else "data/candidates.json"
TOPK = 15

STOP = set("a an the of to in on for and or is are be with by from as at this that "
           "test verify ensure check should must when then if it its each via using use "
           "case cases step steps result results expected device".split())
TOKRE = re.compile(r"[a-z0-9]+")
LEADNUM = re.compile(r"^\s*\(\d+\)\s*")
# Japanese (hiragana, katakana, CJK ideographs, half-width kana)
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿ｦ-ﾟ]")


def is_japanese(c):
    blob = (c.get("title", "") + " " + (c.get("summary") or "") + " " +
            " ".join((s.get("action") or "") + (s.get("expected") or "")
                     for s in (c.get("steps") or [])))
    return bool(CJK.search(blob))


def usable(c):
    """Exclude step-less and Japanese TestLink cases per review criteria."""
    return bool(c.get("steps")) and not is_japanese(c)


def toks(s):
    return [t for t in TOKRE.findall((s or "").lower())
            if t not in STOP and len(t) > 1]


def parse_zephyr_title(title):
    """'(44) IPv4_SNMP - SNMP v1' -> area='IPv4 SNMP', feature='SNMP v1'."""
    t = LEADNUM.sub("", title or "")
    if " - " in t:
        left, right = t.split(" - ", 1)
    else:
        left, right = "", t
    area = left.replace("_", " ").replace("&", " ").strip()
    feature = re.sub(r"\(.*?\)", " ", right).strip() or t.strip()
    return area, feature


def zephyr_query(c):
    area, feature = parse_zephyr_title(c["title"])
    parts = [feature] * 4 + [area] * 2 + [c.get("objective", ""), c.get("script_text", "")]
    for s in c.get("steps", []):
        parts += [s.get("description", ""), s.get("expected", "")]
    return " ".join(parts)


def testlink_text(c):
    parts = [c["title"]] * 3 + [c.get("summary", "")]
    for s in c.get("steps", []):
        parts += [s.get("action", ""), s.get("expected", "")]
    return " ".join(parts)


def snippet(c, n=240):
    s = c.get("summary", "") or ""
    steps = c.get("steps", [])
    if steps:
        s += " | step1: " + (steps[0].get("action", "") or "")[:120]
        if steps[0].get("expected"):
            s += " => " + steps[0]["expected"][:80]
    return re.sub(r"\s+", " ", s)[:n].strip()


def z_snippet(c, n=240):
    if c.get("script_type") == "STEP_BY_STEP":
        steps = c.get("steps", [])
        s = " | ".join((st.get("description", "") or "")[:60] for st in steps[:3])
    else:
        s = c.get("script_text", "") or ""
    if c.get("objective"):
        s = "OBJ: " + c["objective"][:120] + " || " + s
    return re.sub(r"\s+", " ", s)[:n].strip()


def main():
    Z = json.load(open(ZIN))
    T_all = json.load(open(TIN))
    T = [c for c in T_all if usable(c)]
    print(f"zephyr={len(Z)} testlink={len(T)} (filtered from {len(T_all)}: "
          f"dropped {sum(1 for c in T_all if not c.get('steps'))} step-less, "
          f"{sum(1 for c in T_all if c.get('steps') and is_japanese(c))} japanese)",
          file=sys.stderr)
    Tidx = {c["id"]: c for c in T}

    df = Counter(); tdocs = []
    for c in T:
        tf = Counter(toks(testlink_text(c)))
        tdocs.append(tf); df.update(tf.keys())
    N = len(T)
    idf = {w: math.log((N + 1) / (dfw + 1)) + 1 for w, dfw in df.items()}

    inv = defaultdict(list)
    for i, tf in enumerate(tdocs):
        vec = {w: (1 + math.log(c)) * idf[w] for w, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        for w, v in vec.items():
            inv[w].append((i, v / norm))

    out = []
    for zc in Z:
        area, feature = parse_zephyr_title(zc["title"])
        tf = Counter(toks(zephyr_query(zc)))
        qvec = {w: (1 + math.log(c)) * idf.get(w, 0.0) for w, c in tf.items()}
        qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0
        scores = defaultdict(float)
        for w, qv in qvec.items():
            for di, dv in inv.get(w, ()):
                scores[di] += (qv / qnorm) * dv
        top = sorted(scores.items(), key=lambda x: -x[1])[:TOPK]
        cands = [{
            "id": T[di]["id"], "title": T[di]["title"], "suite": T[di].get("suite_top"),
            "score": round(sc, 4), "n_steps": len(T[di].get("steps", [])),
            "snippet": snippet(T[di]),
        } for di, sc in top]
        out.append({
            "key": zc["key"], "title": zc["title"], "folder": zc["folder"],
            "area": area, "feature": feature,
            "has_objective": bool(zc.get("objective")),
            "has_precondition": bool(zc.get("precondition")),
            "n_steps": len(zc.get("steps", [])),
            "self_snippet": z_snippet(zc),
            "candidates": cands,
        })
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"wrote {len(out)} -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
