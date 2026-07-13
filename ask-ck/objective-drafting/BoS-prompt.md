We are resuming work on the Ask CK workbench (server-backed; includes the Objective/Test Case Generator).

This is a fresh session, so you have no persistent memory from the previous one. You must load the current state from the files.

**Step 1: Read these files in this exact order before doing anything else:**

1. `ask-ck/objective-drafting/PROGRESS.md` — This is the single most important file. Read it completely. It contains the current status, what is implemented, technical debt, known issues, prioritized backlog with effort estimates, and handoff instructions.
2. `ask-ck/CK-main/SERVER-README.md` — Read for architecture, how the tool works, running instructions, LLM templating approach, and operational details.
3. `ask-ck/objective-drafting/PLAN-server-backed.md` — Read the full approved plan and design rationale (paths in it are historical).
4. `ask-ck/objective-drafting/LESSONS_LEARNED.md` — Read for key decisions and insights from prior sessions.

After the above, also review:
- Root `README.md` (for overall project context)
- Root `SESSION_STATE.md` (for broader project history)
- The contents of `ask-ck/CK-main/CK_server/` (to see the current code structure)

**Step 2: Once you have read the files, do the following in your response:**

- Briefly summarize the *current state* of the project in your own words (what is working well, what is incomplete or broken, and the overall maturity).
- Clearly state the current top priorities according to `PROGRESS.md`, including any high-priority items and their estimated effort.
- Identify any relevant context from higher-level files (root README, SESSION_STATE.md, or ask-ck/objective-drafting/OBJECTIVE_DRAFTING_PROCESS.md) that should influence our work.
- Ask what I want to focus on in this session, or propose the most logical next step(s) based on the current state.

**Rules for this session and all future sessions:**
- All Ask CK related work, code, and documentation must stay under the `ask-ck/` directory (server code in `ask-ck/CK-main/CK_server/`, generator data/docs in `ask-ck/objective-drafting/`, future tools in `ask-ck/pytest-create/`, `ask-ck/test-composer/`, `ask-ck/zephyr-tool/`).
- Prioritize repeatable process enforcement and repeatable outputs (via prompt templating + structured LLM handling) as described in the plan.
- When making changes, always cross-reference the current `PROGRESS.md` and `SERVER-README.md`.
- At the end of the session, I will use a specific update prompt. Do not preemptively update the state files unless I explicitly ask.

Do not proceed with any implementation or suggestions until you have completed the reading and the summary steps above.
