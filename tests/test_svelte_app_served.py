"""What the server serves where, after the Svelte cutover (ask-ck/plans/PLAN-svelte-cutover.md, 2026-10-30).

"/" and every route in svelte/src/routes.js are the Svelte app's committed dist/index.html; its
hashed assets are at /assets (immutable) and its public/ files at the root; Classic (current/) is
at /classic with its files still at /static; the ATUI restyle is no longer served; unknown paths
still 404 (an explicit route list, not a catch-all).
"""
import os
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
CK_MAIN = REPO / "ask-ck" / "frontend" / "ck-main"
APP = CK_MAIN / "svelte"
DIST = APP / "dist"
CLASSIC = CK_MAIN / "current" / "index.html"


def _routes_js() -> set:
    """The paths of `export const routes = { key: "/path", … }` in Trent's routes.js."""
    src = (APP / "src" / "routes.js").read_text(encoding="utf-8")
    body = src[src.index("export const routes"):]
    body = body[: body.index("};")]
    return set(re.findall(r'^\s*\w+:\s*"(/[^"]*)"', body, re.M))


def test_spa_route_tuple_mirrors_routes_js():
    import CK_server.main as main
    assert set(main.SPA_ROUTES) == _routes_js(), "main.SPA_ROUTES must equal svelte/src/routes.js"


def test_every_spa_route_serves_dist_index_with_no_cache(client):
    import CK_server.main as main
    index = (DIST / "index.html").read_text(encoding="utf-8")
    for path in main.SPA_ROUTES:
        r = client.get(path)
        assert r.status_code == 200, path
        assert r.text == index, path
        assert r.headers.get("cache-control") == "no-cache", path


def test_trailing_slash_redirects_to_the_route(client):
    r = client.get("/generator/", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"].endswith("/generator")


def test_classic_is_at_classic_and_not_at_root(client):
    classic = CLASSIC.read_text(encoding="utf-8")
    r = client.get("/classic")
    assert r.status_code == 200 and r.text == classic
    assert r.headers.get("cache-control") == "no-cache"
    assert client.get("/").text != classic
    assert client.get("/classic?panel=composer").status_code == 200


def test_classic_no_longer_links_to_the_restyle():
    assert 'href="/restyle"' not in CLASSIC.read_text(encoding="utf-8")


def test_restyle_is_unserved(client):
    assert client.get("/restyle").status_code == 404
    assert client.get("/restyle/static/styles.css").status_code == 404


def test_every_file_index_html_references_is_served(client):
    html = (DIST / "index.html").read_text(encoding="utf-8")
    refs = re.findall(r'(?:src|href)="(/[^"]+)"', html)
    assert refs
    for ref in refs:
        r = client.get(ref)
        assert r.status_code == 200, ref
        if ref.startswith("/assets/"):
            assert "immutable" in r.headers.get("cache-control", ""), ref


def test_public_files_are_at_the_root(client):
    for name in ("askck-logo.png", "icons.svg"):
        assert (DIST / name).is_file(), name
        r = client.get(f"/{name}")
        assert r.status_code == 200 and r.content == (DIST / name).read_bytes(), name


def test_favicon_is_still_classics(client):
    want = (CK_MAIN / "current" / "favicon.svg").read_bytes()
    assert client.get("/favicon.svg").content == want
    assert client.get("/favicon.ico").content == want


def test_classic_static_still_served_no_cache(client):
    r = client.get("/static/shared/main.js")
    assert r.status_code == 200 and r.headers.get("cache-control") == "no-cache"


def test_unknown_paths_still_404(client):
    for path in ("/api/nope", "/static/nope.js", "/setup/nope", "/not-a-route", "/assets/nope.js"):
        assert client.get(path).status_code == 404, path


def test_version_stamp_covers_dist():
    import CK_server.main as main
    index = DIST / "index.html"
    st = index.stat()
    try:
        main._build_cache.update(stamp="", at=0.0)
        before = main._static_build_id()
        os.utime(index, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))   # mtime only; bytes unchanged
        main._build_cache.update(stamp="", at=0.0)
        after = main._static_build_id()
    finally:
        os.utime(index, ns=(st.st_atime_ns, st.st_mtime_ns))
        main._build_cache.update(stamp="", at=0.0)
    assert before != after, "/api/version must notice a change under svelte/dist/"
