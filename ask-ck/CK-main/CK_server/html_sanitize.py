"""Minimal allowlist HTML sanitizer (stdlib only — no bleach/nh3 dependency).

The Generator's objective is stored and rendered as rich HTML (`<ul><li>…</li></ul>`)
and is inserted RAW into the browser DOM via innerHTML (generator.js). The objective is
produced by the LLM from corpus text the user did not author, so untrusted/prompt-injected
markup (e.g. `<img src=x onerror=…>`, `<script>`) would otherwise execute as stored XSS.

`sanitize_objective_html` strips everything except a small allowlist of formatting tags and
drops ALL attributes (so no `on*` handlers, `href`/`src`, `style`, etc. can survive). It is
intentionally conservative: the objective only ever needs list + inline-emphasis markup.
"""
from html.parser import HTMLParser
from html import escape

# Tags the objective is allowed to contain. Everything else is unwrapped (kept text,
# dropped tag). No attributes are ever preserved on any tag.
_ALLOWED_TAGS = {"ul", "ol", "li", "b", "i", "strong", "em", "code", "br", "p", "span"}
# Void tags that must not get a closing tag.
_VOID_TAGS = {"br"}
# Tags whose TEXT CONTENT must also be discarded (not just the tag), because their content
# is script/style, never display text.
_DROP_CONTENT_TAGS = {"script", "style"}


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self._drop_depth = 0  # inside a script/style subtree

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _DROP_CONTENT_TAGS:
            self._drop_depth += 1
            return
        if self._drop_depth:
            return
        if tag in _ALLOWED_TAGS:
            if tag in _VOID_TAGS:
                self.out.append(f"<{tag}>")
            else:
                self.out.append(f"<{tag}>")   # attributes deliberately dropped
        # non-allowed, non-drop tags: unwrap (emit nothing; content still flows)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self._drop_depth or tag in _DROP_CONTENT_TAGS:
            return
        if tag in _ALLOWED_TAGS:
            self.out.append(f"<{tag}>" if tag in _VOID_TAGS else f"<{tag}></{tag}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _DROP_CONTENT_TAGS:
            if self._drop_depth:
                self._drop_depth -= 1
            return
        if self._drop_depth:
            return
        if tag in _ALLOWED_TAGS and tag not in _VOID_TAGS:
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if self._drop_depth:
            return
        # Escape text so any stray '<'/'>'/'&' becomes inert.
        self.out.append(escape(data, quote=False))

    def result(self) -> str:
        return "".join(self.out)


def sanitize_objective_html(html: str) -> str:
    """Return the objective HTML with only allowlisted tags, no attributes, and no
    script/style content. Safe to insert via innerHTML. Idempotent."""
    if not html:
        return html or ""
    p = _Sanitizer()
    p.feed(str(html))
    p.close()
    return p.result()
