"""Shared helpers for TestLink / Zephyr data extraction (supporting the Test-cases project).

The Test-cases project improves AWPTCM Manual Test Cases by deriving Objectives from TestLink historical data and enriched Automated (ATPyLib) suites, and records many-to-one mappings.

Credentials are read from environment variables (passed at runtime), never stored
on terrenceb-dl. Internal hosts use self-signed certs, so TLS verification is off.
"""
import os, re, html, ssl, json, sys

JIRA_BASE = "https://jira.atlnz.lc"
TESTLINK_RPC = "https://testlink.atlnz.lc/lib/api/xmlrpc/v1/xmlrpc.php"

# Target scope (discovered in Phase 1)
JIRA_PROJECT_KEY = "AWPTCM"
JIRA_PROJECT_ID = 15310
MASTER_FOLDER = "/New Platform Test (MASTER)"
TESTLINK_PROJECT_ID = "3211"  # "Alliedware Plus"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def need(var):
    v = os.environ.get(var)
    if not v:
        sys.exit(f"ERROR: env var {var} not set")
    return v.strip()


_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t ]+")


def html_to_text(s):
    """Strip HTML tags + entities to a clean single-spaced string."""
    if not s:
        return ""
    s = s.replace("&nbsp;", " ")
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = _WS.sub(" ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()


def dump(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(obj)} records -> {path}", file=sys.stderr)
