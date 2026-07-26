"""Tests for the /process reference page anchor fix (backlog: process-page label drift).

Before the fix, main.py blindly turned every "Step N" text into a link to /#step-N
(a wizard panel with no hash routing) and rendered a nav bar of #Step N anchors that
matched nothing. The fix links the nav to the doc's OWN "## Step N:" headings via
GitHub-style slug ids that exist on the page.
"""
import re
import html as _html


def test_process_page_renders(client):
    r = client.get("/process")
    assert r.status_code == 200
    assert "OBJECTIVE_DRAFTING_PROCESS" in r.text


def test_no_broken_wizard_step_links(client):
    """The old broken forms must be gone: /#step-N and bare '#Step N' hrefs."""
    body = client.get("/process").text
    assert 'href="/#step-' not in body, "leftover wizard-panel deep link"
    assert not re.search(r'href="#Step\s', body), "leftover broken '#Step N' nav anchor"


def test_nav_anchors_resolve_to_real_headings(client):
    """Every nav href="#slug" must point at an <h2 id="slug"> that exists on the page."""
    body = client.get("/process").text
    nav_slugs = set(re.findall(r'<a href="#(step-[^"]+)">', body))
    heading_ids = set(re.findall(r'<h2 id="(step-[^"]+)"', body))
    assert nav_slugs, "expected at least one step nav link"
    missing = nav_slugs - heading_ids
    assert not missing, f"nav links with no matching heading anchor: {missing}"


def test_slugs_are_url_safe(client):
    """Anchor ids must be clean slugs (lowercase, no spaces/punctuation) — not raw heading text."""
    body = client.get("/process").text
    for slug in re.findall(r'<h2 id="(step-[^"]+)"', body):
        assert slug == slug.lower()
        assert " " not in slug
        assert re.fullmatch(r"[a-z0-9-]+", slug), f"non-slug id: {slug}"
