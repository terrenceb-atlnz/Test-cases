"""Read a launched campaign's device-testing output, READ-ONLY (PLAN-test-composer §2.6).

/test-mode writes its queue file and per-case logs in the device-testing repo (logged-output.md):

    <TB>/<FAMILY>/CAMPAIGN-QUEUE-<STAMP>.md            Session facts carry `Driver: ask-ck (<run id>)`
    <TB>/<FAMILY>/<group>-<STAMP>/<id>/work/run<N>.log working logs (framework output for scripts)
    <TB>/<FAMILY>/<group>-<STAMP>/<id>/<id><suffix>.log final logs (/create-logs --auto, manual cases)

This server reads that repo — a sibling of Test-cases on the NFS lab home — and never writes it
(the 2026-09-11 write boundary). The Log Viewer is a port of the ART Log Viewer's DESIGN (author's
permission, 2026-10-09): list a campaign's files, read a file's tail first and "load earlier" in
chunks, download it. Paths are confined to the campaign's own directories.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from paths import ASKCK_ROOT

CHUNK = 64 * 1024


def dt_root() -> Path:
    return Path(os.environ.get("CK_DT_ROOT_SERVER") or (ASKCK_ROOT.parent.parent / "device-testing"))


def find_queue(run_id: str) -> Optional[Path]:
    root = dt_root()
    needle = f"Driver: ask-ck ({run_id})"
    for q in sorted(root.glob("*/*/CAMPAIGN-QUEUE-*.md"), reverse=True):
        try:
            if needle in q.read_text(encoding="utf-8", errors="replace"):
                return q
        except OSError:
            continue
    return None


def _stamp(queue: Path) -> str:
    return queue.stem.replace("CAMPAIGN-QUEUE-", "")


def campaign_dirs(queue: Path) -> List[Path]:
    return sorted(p for p in queue.parent.glob(f"*-{_stamp(queue)}") if p.is_dir())


def parse_results(text: str) -> List[Dict[str, str]]:
    """The queue's `## Results` table → rows keyed by its own header names (lower-cased)."""
    m = re.search(r"^##\s+Results\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return []
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return []
    split = lambda ln: [c.strip() for c in ln.strip("|").split("|")]  # noqa: E731
    head = [h.lower() for h in split(lines[0])]
    rows = []
    for ln in lines[2:]:
        cells = split(ln)
        if len(cells) == len(head):
            rows.append(dict(zip(head, cells)))
    return rows


def campaign(run_id: str) -> Dict[str, Any]:
    q = find_queue(run_id)
    if not q:
        return {"found": False, "queue": None, "results": [], "files": []}
    root = dt_root()
    text = q.read_text(encoding="utf-8", errors="replace")
    files = []
    for d in campaign_dirs(q):
        for p in sorted(d.rglob("*")):
            if p.is_file():
                files.append({"path": str(p.relative_to(root)), "size": p.stat().st_size,
                              "case": p.relative_to(d).parts[0] if len(p.relative_to(d).parts) > 1 else None,
                              "final": p.parent.name != "work" and p.suffix == ".log"})
    return {"found": True, "queue": str(q.relative_to(root)), "results": parse_results(text), "files": files}


def _allowed(run_id: str, rel: str) -> Path:
    q = find_queue(run_id)
    if not q:
        raise FileNotFoundError("no campaign for this run yet")
    root = dt_root().resolve()
    p = (root / rel).resolve()
    allowed = [d.resolve() for d in campaign_dirs(q)] + [q.resolve()]
    if not any(p == a or a in p.parents for a in allowed) or not p.is_file():
        raise PermissionError("not a file of this campaign")
    return p


def read_chunk(run_id: str, rel: str, before: Optional[int] = None) -> Dict[str, Any]:
    """The last CHUNK bytes before `before` (default: the end). NULs and CRs stripped — framework
    logs carry both (TESTBOX-ACCESS §4)."""
    p = _allowed(run_id, rel)
    total = p.stat().st_size
    end = total if before is None else max(0, min(int(before), total))
    start = max(0, end - CHUNK)
    with open(p, "rb") as fh:
        fh.seek(start)
        raw = fh.read(end - start)
    if start > 0:                                   # begin on a line boundary
        nl = raw.find(b"\n")
        if 0 <= nl < len(raw) - 1:
            start += nl + 1
            raw = raw[nl + 1:]
    data = raw.replace(b"\x00", b"").replace(b"\r\n", b"\n").replace(b"\r", b"\n").decode("utf-8", "replace")
    return {"path": rel, "data": data, "start": start, "end": end, "total": total, "has_more_before": start > 0}


def file_path(run_id: str, rel: str) -> Path:
    return _allowed(run_id, rel)
