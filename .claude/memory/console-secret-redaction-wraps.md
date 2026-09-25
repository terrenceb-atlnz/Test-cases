---
name: console-secret-redaction-wraps
description: a secret sent down a switch console comes back in the ECHO, and the console WRAPS long lines — a plain str.replace redaction misses the split key and prints it; match with \s* between every character, scrub fragments, and never print the raw reply
metadata:
  type: feedback
  verified: 2026-09-25
---

**Any script that sends a secret (licence key, password) down a device console must redact the
echo wrap-tolerantly before printing or saving anything.** On 2026-09-25 `license ACCESS <key>` to
the x230 (9600 baud) echoed back split over two lines at the terminal width; the script's
`text.replace(KEY, '<ACCESS-KEY>')` matched nothing and the framework's ACCESS key from
`/home/st-art/feature_license_keys.env` went into the session output and two tb470 files (scrubbed
afterwards; the session transcript under `~/.claude/projects/` kept it).

**Why:** AW+ consoles hard-wrap long echoed input (`\r\n` mid-token) — the framework's own logs show
the same wrap on long `sudo mv` lines. Redaction that assumes the secret arrives contiguous fails
silently, and the failure IS the leak.

**How to apply:** build `re.compile(r'\s*'.join(re.escape(ch) for ch in key))`, substitute it, then
replace every 12-character slice of the key that survives; redact exception messages too (a console
error's tail can carry the echo); test the redactor offline against a wrapped sample BEFORE the run;
print only the redacted report. Also: the AW+ `license <name> <key>` command asks "A restart of
affected modules may be required. Would you like to continue? (y/n)" — answer `y` + Enter
([[awplus-cli-confirmations-need-enter]]). Never put the key itself in any memory or file.
