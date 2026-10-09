"""Run e-mail for Test Composer / Validation (PLAN-agent-sessions §8, D5; PLAN-test-composer C-D4).

The SERVER sends it, never the seat: smtplib → localhost:25 (this host's postfix) → relayhost
int-smtp.atlnz.lc, from do-not-reply@alliedtelesis.co.nz — the same route as ART's `rtmt -m`,
verified end to end 2026-10-09 (one test mail, received ~6 s later). Plain text, short.

CK_MAIL_DISABLE=1 turns sending off (the specs patch `_smtp` instead). A failure never raises
into the caller: it returns the error, and the run record keeps it.
"""
from __future__ import annotations

import os
import smtplib
import socket
from email.mime.text import MIMEText
from typing import List, Optional

FROM = "do-not-reply@alliedtelesis.co.nz"


def _smtp():
    return smtplib.SMTP("localhost", 25, timeout=20)


def send(to: List[str], subject: str, body: str) -> Optional[str]:
    """Send one mail. Returns None on success, else the error text."""
    to = [t.strip() for t in to if t and t.strip()]
    if not to:
        return "no recipient"
    if os.environ.get("CK_MAIL_DISABLE") == "1":
        return "mail disabled (CK_MAIL_DISABLE=1)"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = FROM
    msg["To"] = ", ".join(to)
    try:
        s = _smtp()
        try:
            refused = s.sendmail(FROM, to, msg.as_string())
        finally:
            s.quit()
        return f"refused: {refused}" if refused else None
    except (OSError, smtplib.SMTPException, socket.error) as e:
        return f"{type(e).__name__}: {e}"


def notice_mail(record: dict, notices: list, link: str) -> tuple:
    """D5: an informative mail, not a request — which run, and for each notice its scope, what it
    needed and what it did. Notices that arrive together go in ONE mail (the 2026-10-09 E2E sent
    three identical-looking mails a second apart)."""
    scopes = sorted({n["scope"] for n in notices})
    subject = (f"Ask-CK {record['kind']} {record['run_id']}: "
               + (f"notice for {scopes[0]}" if len(notices) == 1 else f"{len(notices)} notices ({', '.join(scopes)})"))
    parts = [f"Run {record['run_id']} on {record['testbox']} carried on past something it needed a person for.\n"]
    for i, n in enumerate(notices, 1):
        parts.append(f"{i}. Scope:          {n['scope']}\n   What it needed: {n['needed']}\n   What it did:    {n['did']}\n")
    parts.append(f"\nThe campaign did not stop (decision D5). Details and re-grading: {link}\n")
    return subject, "\n".join(parts)


def finish_mail(record: dict, counts: dict, link: str) -> tuple:
    state = record.get("state")
    tally = ", ".join(f"{v} {k}" for k, v in sorted(counts.items())) or "no results"
    subject = f"Ask-CK {record['kind']} {record['run_id']} {state}: {tally}"
    lines = [f"Run {record['run_id']} on {record['testbox']} ended: {state}.", "",
             f"Results: {tally}"]
    if record.get("cost_usd") is not None:
        lines.append(f"Cost (list-price estimate): ${record['cost_usd']:.2f}")
    if record.get("tokens"):
        lines.append(f"Tokens: {record['tokens']:,}")
    if record.get("error"):
        lines.append(f"Error: {record['error']}")
    for n in record.get("notices") or []:
        lines.append(f"Notice ({n['scope']}): {n['needed']} -> {n['did']}")
    lines += ["", f"Results table and logs: {link}"]
    return subject, "\n".join(lines) + "\n"
