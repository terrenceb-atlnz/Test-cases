"""The server serves the seat setup — scripts, agents and a manifest — from ask-ck/agent/.

WHY (2026-09-10, demo day). A Windows seat had the Ask CK URL and nothing else: no repo,
no Git, no Python, no agent. The browser cannot run Claude on the seat, the agent is the
only bridge, and nothing delivered one. So the server itself serves the setup one-liners'
targets (PLAN-seat-setup-and-per-seat-llm.md §3.1). These pin:

  * only the allowlisted names are served — README, __pycache__, traversal all 404;
  * the manifest's hashes match the bytes a seat downloads (the setup scripts verify
    downloads against it, so a mismatch here would make every setup fail closed);
  * the server's origin is templated into the setup scripts from the request Host, and
    the AGENT files are served byte-identical to the repo files;
  * the manifest's agent_version is the version both agents declare.
"""
import hashlib
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "agent"))
import ck_agent  # noqa: E402

AGENT_DIR = _REPO / "ask-ck" / "agent"


def test_manifest_lists_every_served_file_with_matching_hashes(client):
    r = client.get("/setup/manifest.json", headers={"host": "10.33.22.17:8000"})
    assert r.status_code == 200
    m = r.json()
    assert set(m["files"]) == {"setup.ps1", "setup.sh", "ck-agent.ps1", "ck_agent.py"}
    assert m["agent_version"] == ck_agent.AGENT_VERSION
    assert m["server"] == "http://10.33.22.17:8000"
    for name, sha in m["files"].items():
        body = client.get(f"/setup/{name}", headers={"host": "10.33.22.17:8000"}).content
        assert hashlib.sha256(body).hexdigest() == sha, f"{name}: manifest hash != served bytes"
    assert m["one_liners"]["windows"] == "irm http://10.33.22.17:8000/setup/setup.ps1 | iex"
    assert m["one_liners"]["ubuntu"] == "curl -fsSL http://10.33.22.17:8000/setup/setup.sh | bash"


def test_agent_files_are_served_byte_identical_to_the_repo(client):
    for name in ("ck_agent.py", "ck-agent.ps1"):
        served = client.get(f"/setup/{name}").content
        assert served == (AGENT_DIR / name).read_bytes(), f"{name} differs from the repo file"


def test_setup_scripts_carry_the_requesting_origin_not_the_placeholder(client):
    for name in ("setup.sh", "setup.ps1"):
        text = client.get(f"/setup/{name}", headers={"host": "ck-box.lan:9000"}).text
        assert "__CK_SERVER__" not in text, f"{name} still carries the placeholder"
        assert "http://ck-box.lan:9000" in text
        # and the repo copy DOES carry it, so the templating has something to replace
        assert "__CK_SERVER__" in (AGENT_DIR / name).read_text(encoding="utf-8")


def test_forwarded_headers_win_behind_a_proxy(client):
    text = client.get("/setup/setup.sh", headers={"host": "127.0.0.1:8000",
                                                  "x-forwarded-host": "askck.example",
                                                  "x-forwarded-proto": "https"}).text
    assert "https://askck.example" in text


def test_only_allowlisted_names_are_served(client):
    for bad in ("README.md", "run-agent.sh", "__pycache__", "..%2Fmain.py", "ck_agent.pyc", ""):
        r = client.get(f"/setup/{bad}")
        assert r.status_code == 404, f"/setup/{bad!r} answered {r.status_code}"


def test_served_scripts_are_not_cached_by_the_browser(client):
    r = client.get("/setup/setup.ps1")
    assert r.headers.get("cache-control") == "no-cache"
    assert r.headers["content-type"].startswith("text/plain")


def test_setup_scripts_verify_downloads_against_the_manifest():
    """Structural: a script that downloads without checking would install whatever a
    misconfigured server handed it. Both compare sha256 against manifest.json."""
    sh = (AGENT_DIR / "setup.sh").read_text(encoding="utf-8")
    ps = (AGENT_DIR / "setup.ps1").read_text(encoding="utf-8")
    assert "setup/manifest.json" in sh and "sha256sum" in sh and "does not match the server's manifest" in sh
    assert "setup/manifest.json" in ps and "Get-FileHash" in ps and "does not match the server's manifest" in ps
    # and both hand the last word to the page
    assert "?seat-check=1" in sh and "?seat-check=1" in ps
    # and both refuse to run as the wrong user / ask before autostart (D6)
    assert "Do not run this as root" in sh
    assert "automatically when you log in" in sh and "automatically when you log in" in ps
