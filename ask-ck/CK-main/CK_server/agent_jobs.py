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
    __slots__ = ("id", "prompt", "model", "event", "result", "created")

    def __init__(self, prompt: str, model: str):
        self.id = uuid.uuid4().hex
        self.prompt = prompt
        self.model = model
        self.event = threading.Event()
        self.result: Optional[dict] = None
        self.created = time.time()


class AgentJobRegistry:
    """Thread-safe queue of pending prompt jobs, partitioned by session id."""

    def __init__(self, max_idle_seconds: int = 1800):
        self._lock = threading.Lock()
        self._queues: Dict[str, Deque[_Job]] = {}      # session_id -> FIFO of unclaimed jobs
        self._inflight: Dict[str, _Job] = {}           # job_id -> job awaiting a result
        self._session_seen: Dict[str, float] = {}      # session_id -> last poll time
        self._max_idle = max_idle_seconds

    # --- producer side (LLM caller thread) ---------------------------------
    def submit(self, session_id: str, prompt: str, model: str, timeout: int) -> dict:
        """Enqueue a job and BLOCK until the browser posts its result or timeout.

        Returns {content, error}. On timeout returns an error dict (never raises).
        """
        job = _Job(prompt, model)
        with self._lock:
            self._queues.setdefault(session_id, deque()).append(job)
            self._inflight[job.id] = job
        got = job.event.wait(timeout=timeout)
        with self._lock:
            self._inflight.pop(job.id, None)
            # If it was never claimed, drop it from the queue too.
            q = self._queues.get(session_id)
            if q and job in q:
                try:
                    q.remove(job)
                except ValueError:
                    pass
        if not got:
            return {"content": ("ERROR: local Claude agent did not respond in time. "
                                "Is ck-agent running on your machine and this tab open?"),
                    "error": True, "timeout": True}
        return job.result or {"content": "ERROR: empty agent result", "error": True}

    # --- consumer side (browser via /api/agent) ----------------------------
    def next_job(self, session_id: str) -> Optional[Tuple[str, str, str]]:
        """Claim the next queued job for a session. Returns (job_id, prompt, model) or None."""
        with self._lock:
            self._session_seen[session_id] = time.time()
            q = self._queues.get(session_id)
            if not q:
                return None
            job = q.popleft()
            return job.id, job.prompt, job.model

    def deliver(self, job_id: str, content: str, error: bool, usage: Optional[dict] = None,
                total_cost_usd: Optional[float] = None) -> bool:
        """Browser posts a completion. Wakes the blocked caller. True if job existed.

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
