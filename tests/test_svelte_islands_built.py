"""The Svelte islands' committed bundles are built from their current sources (PLAN-test-composer §6).

current/islands/*.js is COMMITTED build output: the hosted server only serves files, and the working
tree is production. So a source edit under current/svelte-src/ that is not rebuilt would ship the OLD
page while the spec of the NEW one passes against... the old bundle. vite.config.js stamps every
bundle with `source-sha256:<hex>` over the sorted sources; this recomputes that hash (the same
algorithm, mirrored here) and fails when they differ. Fix: `npm run build` in current/svelte-src/.
"""
import hashlib
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
CURRENT = REPO / "ask-ck" / "frontend" / "ck-main" / "current"
SRC = CURRENT / "svelte-src"
ISLANDS = CURRENT / "islands"


def _source_hash() -> str:
    files = [p for p in (SRC / "src").rglob("*") if p.is_file()]
    files += [SRC / n for n in ("vite.config.js", "package.json", "package-lock.json")]
    rels = sorted(p.relative_to(SRC).as_posix() for p in files)
    h = hashlib.sha256()
    for rel in rels:
        h.update((rel + "\n").encode())
        h.update((SRC / rel).read_bytes())
        h.update(b"\n")
    return h.hexdigest()


def test_every_island_bundle_matches_its_sources():
    bundles = sorted(ISLANDS.glob("*.js"))
    assert bundles, "no built islands under current/islands/"
    want = _source_hash()
    for b in bundles:
        m = re.search(r"source-sha256:([0-9a-f]{64})", b.read_text(encoding="utf-8")[:400])
        assert m, f"{b.name} has no source-sha256 banner: was it built by svelte-src/vite.config.js?"
        assert m.group(1) == want, (
            f"{b.name} is stale: built from sources hashing {m.group(1)[:12]}…, the sources now hash "
            f"{want[:12]}… — run `npm run build` in ask-ck/frontend/ck-main/current/svelte-src/")


def test_the_lock_file_is_committed_with_the_sources():
    # The hash covers package-lock.json, so a rebuild on another seat resolves the same versions.
    assert (SRC / "package-lock.json").is_file()


def test_every_island_a_page_imports_exists():
    for js in CURRENT.rglob("*.js"):
        if "svelte-src" in js.parts or "islands" in js.parts:
            continue
        for name in re.findall(r"""import\(\s*['"]\.\./islands/([\w-]+\.js)['"]\s*\)""", js.read_text(encoding="utf-8")):
            assert (ISLANDS / name).is_file(), f"{js.relative_to(CURRENT)} imports islands/{name}, which is not built"
