"""Per-session job registry for the browser-brokered Claude agent.

When a session's auth_method is "claude_agent", the server does NOT run `claude`.
It enqueues the prompt as a job keyed to that browser session; the user's browser
long-polls for it, runs it on the user's own machine (via ck-agent), and posts the
completion back. The original synchronous LLM caller blocks here on a threading
primitive until that result arrives (or times out).

See ask-ck/CK-main/PLAN-per-user-agent.md.
"""
import threading
import time
import uuid
from collections import deque
from typing import Dict, Optional, Deque, Tuple


class _Job:
    __slots__ = ("id", "session_id", "prompt", "model", "timeout", "event", "result",
                 "created", "claimed_at", "system")

    def __init__(self, session_id: str, prompt: str, model: str, timeout: int = 0,
                 system: str = ""):
        self.id = uuid.uuid4().hex
        self.session_id = session_id      # owning browser session — enforced on deliver
        self.prompt = prompt
        self.model = model
        # The caller's system steer, carried to the user's ck-agent as the CLI's
        # `--system-prompt` (2026-09-04). Before this the agent path ran every call under
        # the CLI's own harness prompt, with tools, and unsteered — see llm._call_claude_agent.
        self.system = system
        # The server's own wait, carried so the browser can give its ck-agent the SAME
        # budget. It used to be dropped here and the browser hard-coded 600s, so the two
        # ends disagreed: a gather_fragments call asked for 300s, the server gave up at
        # 300s, and the user's machine kept working for up to 600s on a result that was
        # discarded on arrival (observed 2026-08-27, AWPTCM-T44191, 300000ms, no usage).
        self.timeout = timeout
        self.event = threading.Event()
        self.result: Optional[dict] = None
        self.created = time.time()
        # Set by next_job when a browser actually takes the job. `_inflight` cannot
        # answer this -- submit puts the job there immediately, so it means "awaiting a
        # result", not "someone is working on it". The distinction is what lets submit
        # fail fast on an absent agent instead of burning the model's whole budget.
        self.claimed_at: Optional[float] = None


# How long to wait for SOME browser to claim a queued job before giving up on it.
# agent.js long-polls with wait=25, so a live broker claims within ~25s plus overhead;
# 60 leaves room for a reload or a slow first poll without making an absent agent
# expensive. This bounds only PICKUP -- the work itself gets the caller's full budget.
_PICKUP_GRACE_SECONDS = 60

# How recently a session must have polled to count as PRESENT.
#
# The pickup deadline alone is not enough evidence to abandon a job, and shipping it that
# way was a regression (2026-09-02, AWPTCM-T44297): "nobody claimed this" and "nobody is
# there" are different statements, and only the second justifies giving up. A broker that
# is BUSY running a job is not polling either -- one loop, one job at a time -- so a second
# LLM action queued during a long generate looked exactly like an absent agent and was
# failed at 60s. Before the pickup grace existed it would have waited and been served when
# the broker came free.
#
# So presence is tested on two signals, either of which is sufficient:
#   1. the session polled within this window (next_job stamps _session_seen), or
#   2. the session is holding a job it has already claimed (busy, and coming back).
# Only when NEITHER holds is the agent genuinely gone.
_SESSION_PRESENT_WINDOW = 60


class AgentJobRegistry:
    """Thread-safe queue of pending prompt jobs, partitioned by session id."""

    def __init__(self, max_idle_seconds: int = 1800):
        self._lock = threading.Lock()
        self._queues: Dict[str, Deque[_Job]] = {}      # session_id -> FIFO of unclaimed jobs
        self._inflight: Dict[str, _Job] = {}           # job_id -> job awaiting a result
        self._session_seen: Dict[str, float] = {}      # session_id -> last poll time
        self._max_idle = max_idle_seconds
        self._last_gc = time.time()

    # --- producer side (LLM caller thread) ---------------------------------
    def submit(self, session_id: str, prompt: str, model: str, timeout: int,
               on_start=None, system: str = "") -> dict:
        """Enqueue a job and BLOCK until the browser posts its result or timeout.

        Returns {content, error}. On timeout returns an error dict (never raises).
        `on_start(job)` (optional, 2026-08-26) is called once the job is queued —
        the LLM layer uses it to attach a cancel handle that stamps a cancelled
        result and sets the job's Event, waking this wait early.
        `system` (2026-09-04) is the steer the agent passes as `--system-prompt`.
        """
        job = _Job(session_id, prompt, model, timeout, system=system)
        with self._lock:
            self._queues.setdefault(session_id, deque()).append(job)
            self._inflight[job.id] = job
        if on_start is not None:
            try:
                on_start(job)
            except Exception:
                pass  # a broken cancel hook must not break the call itself
        # TWO PHASES, because "nobody took the job" and "the work is taking a while" are
        # different failures and only one of them deserves the model's whole budget.
        #
        # THE DEFECT THIS FIXES (2026-09-01, AWPTCM-T33351)
        # ------------------------------------------------
        # This used to be a single `wait(timeout)`. A generate was enqueued for a browser
        # whose broker loop had died two minutes earlier (a frozen background tab wedged
        # `ckBrokerRunning`; see agent.js), so nothing ever claimed it -- and the caller
        # sat here for the FULL budget before reporting "did not respond in time". At the
        # old 600s that was ten wasted minutes; once generate_script's budget was floored
        # to 1800s it became thirty. The message was also misleading: it says "did not
        # respond", when in fact nothing had ever picked the job up.
        #
        # Phase 1 -- PICKUP. A browser polls every ~25s, so a job unclaimed after
        # _PICKUP_GRACE_SECONDS is not going to be claimed; report that immediately, and
        # say plainly that no agent took it rather than blaming a slow response.
        #
        # Phase 2 -- WORK. Once claimed, wait out the remaining budget with NO liveness
        # check. That is deliberate and load-bearing: agent.js stops long-polling while it
        # runs a job (it is awaiting its local ck-agent, not the server), so `_session_seen`
        # goes stale for the whole duration of every LEGITIMATE long call. Failing on
        # session staleness here would kill exactly the 300-800s generations this budget
        # exists for. A tab that freezes AFTER claiming still costs the full budget; that
        # is the accepted residual, and the client-side liveness fix is what shrinks it.
        grace = min(_PICKUP_GRACE_SECONDS, timeout)
        got = job.event.wait(timeout=grace)
        claimed = job.claimed_at is not None
        if not got and not claimed and not self.session_present(session_id):
            self._retire(job, session_id)
            return {"content": ("ERROR: no local Claude agent picked up this job within "
                                f"{grace}s, and nothing has polled for this browser session "
                                "since. The tab that brokers your Claude seat is not running "
                                "its loop — reload the Ask CK tab, check the LLM mode is "
                                "'Claude Code CLI (my local machine)', and confirm ck-agent "
                                "is running with 'Check my local agent'."),
                    "error": True, "timeout": True, "unclaimed": True}
        if not got:
            got = job.event.wait(timeout=max(0, timeout - grace))
        self._retire(job, session_id)
        if not got:
            return {"content": ("ERROR: local Claude agent did not respond in time. "
                                "Is ck-agent running on your machine and this tab open?"),
                    "error": True, "timeout": True}
        return job.result or {"content": "ERROR: empty agent result", "error": True}

    def is_wanted(self, job_id: str) -> bool:
        """Is this job still awaited by a caller?

        False the instant `submit` returns -- cancelled, timed out, or already delivered.
        The browser polls this WHILE it runs a job so it can abandon work nobody wants.

        THE DEFECT THIS EXISTS FOR (2026-09-02, AWPTCM-T44297)
        -----------------------------------------------------
        Cancel was server-side only, and `_call_claude_agent` says so plainly: "the user's
        local agent may still finish its call on their own machine, but the result is
        discarded". The undocumented consequence is that the BROKER is stuck too -- it is
        inside `await fetch(ck-agent/run)`, so it stops long-polling for the whole remaining
        duration of work that has already been thrown away. Measured: a generate was
        cancelled 6.8s in at 16:13:22; the loop's last poll was 16:13:16 and it never polled
        again, so the Extract Sequence clicked a minute later had nobody to claim it. With
        budgets floored to 1800s that is up to half an hour of dead broker after every Stop.
        """
        with self._lock:
            return job_id in self._inflight

    def session_present(self, session_id: str) -> bool:
        """Is a broker for `session_id` alive -- polling, or busy on a claimed job?

        Both signals matter and neither alone is sufficient:
          * _session_seen goes stale during a LEGITIMATE long run, because agent.js stops
            long-polling while it awaits its local ck-agent. A 500s generate leaves the
            session unseen for 500s, so freshness alone would abandon real work.
          * a claimed job proves someone took work, but an idle broker holds none, so the
            claim signal alone would abandon a healthy idle agent.

        The caller's own job cannot pollute this: only CLAIMED jobs count, and a caller
        only asks while its job is unclaimed. An `exclude` parameter was written for that
        case and removed -- it was unreachable, and a mutation test proved it (deleting it
        changed no behaviour and failed nothing).
        """
        now = time.time()
        with self._lock:
            last = self._session_seen.get(session_id, 0.0)
            if last and (now - last) <= _SESSION_PRESENT_WINDOW:
                return True
            return any(job.session_id == session_id and job.claimed_at is not None
                       for job in self._inflight.values())

    def _retire(self, job: "_Job", session_id: str) -> None:
        """Drop a finished/abandoned job from both structures. Was inline in submit;
        extracted because the two-phase wait has two exit points and a job left in
        `_queues` would be handed to the next poller as if it were live work."""
        with self._lock:
            self._inflight.pop(job.id, None)
            q = self._queues.get(session_id)
            if q and job in q:
                try:
                    q.remove(job)
                except ValueError:
                    pass

    # --- consumer side (browser via /api/agent) ----------------------------
    def next_job(self, session_id: str) -> Optional[Tuple[str, str, str, int, str]]:
        """Claim the next queued job. Returns (job_id, prompt, model, timeout, system) or None.

        `timeout` is the server's own remaining patience, so the browser can bound its
        local agent by the same number instead of a hard-coded one of its own."""
        with self._lock:
            self._session_seen[session_id] = time.time()
            q = self._queues.get(session_id)
            if q is not None and not q:
                # Drop the empty deque rather than leaving an entry keyed by a
                # client-supplied session header.
                self._queues.pop(session_id, None)
            job = q.popleft() if q else None
        # gc() existed but had ZERO call sites, so _queues/_session_seen grew for the
        # lifetime of the process, keyed by an unvalidated header. Drive it from the
        # long-poll (the one call that runs continuously), rate-limited so it costs
        # nothing per request. Outside the lock — gc() takes it itself.
        self._maybe_gc()
        if job is None:
            return None
        job.claimed_at = time.time()      # submit's phase-1 signal; see _Job.claimed_at
        return job.id, job.prompt, job.model, job.timeout, job.system

    def _maybe_gc(self) -> None:
        """Run gc() at most once per half-idle-window."""
        interval = max(60, self._max_idle // 2)
        now = time.time()
        with self._lock:
            due = (now - self._last_gc) >= interval
            if due:
                self._last_gc = now
        if due:
            self.gc()

    def deliver(self, job_id: str, content: str, error: bool, usage: Optional[dict] = None,
                total_cost_usd: Optional[float] = None, session_id: Optional[str] = None) -> bool:
        """Browser posts a completion. Wakes the blocked caller. True if job existed.

        `session_id`, when provided, MUST match the job's owning session — otherwise the
        deliver is rejected (returns False). This stops a caller from posting a result for
        another session's in-flight job by guessing/observing its job_id (adversarial-review
        finding: the bridge previously keyed delivery on job_id alone).

        `usage` / `total_cost_usd` are optional token accounting the ck-agent lifts
        from the Claude CLI's JSON envelope. When present they ride the result dict
        in the exact shape llm_debug.normalize_usage expects (usage sub-dict +
        top-level total_cost_usd), so the token badge + debug-log populate for this
        transport; when absent the log honestly shows "— tok".
        """
        with self._lock:
            job = self._inflight.get(job_id)
            if not job:
                return False
            if session_id is not None and job.session_id != session_id:
                return False   # job belongs to a different session — refuse
        job.result = {
            "content": content,
            "error": bool(error),
            **({"usage": usage} if usage else {}),
            **({"total_cost_usd": total_cost_usd} if total_cost_usd is not None else {}),
        }
        job.event.set()
        return True

    # --- health / housekeeping ---------------------------------------------
    def session_active(self, session_id: str, within: int = 20) -> bool:
        """Has this session polled recently (i.e. is a broker tab attached)?"""
        with self._lock:
            last = self._session_seen.get(session_id)
        return bool(last and (time.time() - last) <= within)

    def pending_count(self, session_id: str) -> int:
        with self._lock:
            return len(self._queues.get(session_id) or ())

    def gc(self):
        """Drop idle session queues so a churn of tabs doesn't leak memory."""
        now = time.time()
        with self._lock:
            stale = [s for s, t in self._session_seen.items() if now - t > self._max_idle]
            for s in stale:
                self._session_seen.pop(s, None)
                self._queues.pop(s, None)


# Module-level singleton shared by the bridge router and llm.py.
registry = AgentJobRegistry()
