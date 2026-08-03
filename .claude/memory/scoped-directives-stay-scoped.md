---
name: scoped-directives-stay-scoped
description: A short directive applies to the layer under discussion, not to every layer it could plausibly touch — apply it there and name the others rather than assuming
metadata:
  type: feedback
---

Terrence's directives are often one line and land mid-topic. **Apply them to the thing being
discussed, and say out loud what you are NOT applying them to.**

The case that produced this (2026-08-03, Phase −1): the decision on 43 already-live Zephyr cases
was *"I dont want a snapshot, i want a working copy. no version control required."* That was
about **Zephyr** — stay at v2.0, overwrite in place, no v3.0, no upstream version trail. I read
"snapshot" as a general position and also stripped the local `push.intent` audit record's capture
of the prior objective/testScript. He corrected it: *"i feel like you might have taken a comment
out of context here. This is contextually-limited to Zephyr."*

**Why:** over-generalising removes things he never asked to remove, and the removal is invisible
to him — he sees the reply, not the diff. Worse here, the Zephyr decision was the very *reason*
to keep the local record: with no version trail upstream, a re-push that writes a worse objective
over a better one is unrecoverable. Generalising inverted the intent.

**How to apply:** when a directive could bind at more than one layer (upstream system / local
tooling / repo / tests), bind it to the layer in the conversation. If another layer looks
affected, name it in one clause and let him extend the ruling — don't extend it yourself. Same
discipline as [[mutate-before-you-claim]]: state the scope of the claim you are acting on.
Related: [[user-prefers-manual-ui-testing]].
