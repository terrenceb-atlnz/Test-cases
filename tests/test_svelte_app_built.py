"""The Svelte app's committed build (svelte/dist/) is built from its current sources (PLAN-svelte-cutover.md).

ask-ck/frontend/ck-main/svelte/dist/ is COMMITTED build output, the same rule as the islands
(tests/test_svelte_islands_built.py): the hosted server only serves files and the working tree is
production, so a source edit under svelte/ that is not rebuilt would ship the OLD app while the
specs of the NEW one pass against the source. ask-ck/tools/build_svelte_app.sh stamps
dist/.source-sha256 over the sorted sources; this recomputes that hash (same algorithm, mirrored
here) and fails when they differ. Fix: run ask-ck/tools/build_svelte_app.sh and commit dist/.
"""
import hashlib
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
APP = REPO / "ask-ck" / "frontend" / "ck-main" / "svelte"
DIST = APP / "dist"
_TOP = ("index.html", "vite.config.js", "svelte.config.js", "package.json", "package-lock.json")
_FIX = "run ask-ck/tools/build_svelte_app.sh and commit ask-ck/frontend/ck-main/svelte/dist/"


def _source_hash() -> str:
    files = [p for d in ("src", "public") for p in (APP / d).rglob("*") if p.is_file()]
    files += [APP / n for n in _TOP]
    rels = sorted(p.relative_to(APP).as_posix() for p in files)
    h = hashlib.sha256()
    for rel in rels:
        h.update((rel + "\n").encode())
        h.update((APP / rel).read_bytes())
        h.update(b"\n")
    return h.hexdigest()


def test_dist_matches_its_sources():
    stamp = DIST / ".source-sha256"
    assert stamp.is_file(), f"no svelte/dist/.source-sha256 — {_FIX}"
    got = stamp.read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"[0-9a-f]{64}", got), f"malformed stamp {got!r} — {_FIX}"
    want = _source_hash()
    assert got == want, (
        f"svelte/dist is stale: built from sources hashing {got[:12]}…, the sources now hash "
        f"{want[:12]}… — {_FIX}")


def test_every_file_index_html_references_is_in_dist():
    html = (DIST / "index.html").read_text(encoding="utf-8")
    refs = re.findall(r'(?:src|href)="(/[^"]+)"', html)
    assert refs, "dist/index.html references nothing — was it built?"
    for ref in refs:
        assert (DIST / ref.lstrip("/")).is_file(), f"dist/index.html references {ref}, which is not in dist/"


def test_the_lock_file_is_committed_with_the_sources():
    # The hash covers package-lock.json, so a rebuild on another seat resolves the same versions.
    assert (APP / "package-lock.json").is_file()
