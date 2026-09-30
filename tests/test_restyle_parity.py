"""The ATUI restyle (ask-ck/plans/PLAN-atui-restyle.md) shares current/'s JS, so it must carry
every hook that JS binds to.

restyle/index.html is its own page (S1) but loads /static/shared/main.js, which finds its
elements by id and dispatches clicks by data-action. A hook present in current/index.html
and missing from restyle/index.html breaks that feature in the ATUI UI only, and silently —
the page still loads. These tests make that drift loud (§2.5).
"""
from html.parser import HTMLParser
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
CK_MAIN = REPO / "ask-ck" / "frontend" / "ck-main"
CURRENT = CK_MAIN / "current" / "index.html"
RESTYLE = CK_MAIN / "restyle" / "index.html"


class _Hooks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.actions, self.classes = set(), set(), set()
        self.html_attrs = {}
        self.links = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_attrs = a
        if "id" in a:
            self.ids.add(a["id"])
        if "data-action" in a:
            self.actions.add(a["data-action"])
        self.classes.update((a.get("class") or "").split())
        if tag == "a" and "ui-toggle-opt" in (a.get("class") or ""):
            self.links[a.get("href")] = a


def _parse(path):
    p = _Hooks()
    p.feed(path.read_text(encoding="utf-8"))
    return p


def test_every_id_in_current_exists_in_restyle():
    missing = _parse(CURRENT).ids - _parse(RESTYLE).ids
    assert not missing, f"restyle/index.html lacks ids the shared JS may bind to: {sorted(missing)}"


def test_every_data_action_in_current_exists_in_restyle():
    missing = _parse(CURRENT).actions - _parse(RESTYLE).actions
    assert not missing, f"restyle/index.html lacks data-actions: {sorted(missing)}"


def test_sidebar_logo_hook_survives():
    # shared/main.js binds the hidden admin panel's double-click to .sidebar-logo (S13).
    assert "sidebar-logo" in _parse(RESTYLE).classes


def test_both_pages_load_the_same_shared_entry_point():
    pat = re.compile(r'<script type="module" src="(/static/shared/main\.js\?v=\d+)"')
    cur = pat.findall(CURRENT.read_text(encoding="utf-8"))
    rs = pat.findall(RESTYLE.read_text(encoding="utf-8"))
    assert cur and cur == rs, f"main.js tags differ: current {cur} vs restyle {rs}"


def test_only_restyle_carries_the_atui_flag():
    assert _parse(RESTYLE).html_attrs.get("data-ui") == "atui"
    assert "data-ui" not in _parse(CURRENT).html_attrs


def test_restyle_uses_its_own_stylesheet():
    html = RESTYLE.read_text(encoding="utf-8")
    assert 'href="/restyle/static/styles.css' in html
    assert 'href="/static/styles.css' not in html


def test_swap_control_points_each_way():
    assert "/restyle" in _parse(CURRENT).links, "Classic's swap control must link to /restyle"
    assert "/" in _parse(RESTYLE).links, "restyle's swap control must link back to / (Classic)"


def test_colour_specimen_is_identical_in_both_pages():
    # The Test Composer TBD page carries a Classic-vs-ATUI specimen (Terrence 2026-09-30). It is
    # only a 1-to-1 comparison if the markup is the same in both pages.
    pat = re.compile(r"<!-- ck-specimen:start.*?<!-- ck-specimen:end -->", re.S)
    cur = pat.findall(CURRENT.read_text(encoding="utf-8"))
    rs = pat.findall(RESTYLE.read_text(encoding="utf-8"))
    assert len(cur) == 1 and cur == rs, "the specimen differs between current/ and restyle/"


def test_restyle_route_serves_the_restyle_page(client):
    r = client.get("/restyle")
    assert r.status_code == 200 and 'data-ui="atui"' in r.text


def test_root_still_serves_current(client):
    r = client.get("/")
    assert r.status_code == 200 and 'data-ui="atui"' not in r.text


def test_restyle_static_serves_its_own_files(client):
    assert client.get("/restyle/static/styles.css").status_code == 200
    assert client.get("/restyle/static/atui/fonts/inter-latin-wght-normal.woff2").status_code == 200


def test_both_pages_apply_the_saved_theme_before_first_paint():
    # Terrence 2026-09-30: swapping in light mode flashed dark, because the page ships
    # class="dark" and shared/theme.js runs only after the module graph loads. An inline
    # <head> script must set the class before any stylesheet is applied.
    for page in (CURRENT, RESTYLE):
        html = page.read_text(encoding="utf-8")
        boot = html.find("localStorage.getItem('theme')")
        sheet = html.find('<link rel="stylesheet"')
        assert boot != -1, f"{page.parent.name}/index.html has no pre-paint theme script"
        assert boot < sheet, f"{page.parent.name}/index.html applies the theme after its stylesheet"
