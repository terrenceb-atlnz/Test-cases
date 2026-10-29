// The stale-tab guard (versionService.js, ported from current/shared/version.js 2026-10-30).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchBuild, startVersionWatch } from "../../src/lib/services/versionService.js";

function fakeFetch(builds) {
  // Each call answers with the next entry: a build id string, "" for a non-ok reply, or an Error to throw.
  let i = 0;
  return vi.fn(async () => {
    const b = builds[Math.min(i++, builds.length - 1)];
    if (b instanceof Error) throw b;
    if (b === "") return { ok: false, json: async () => ({}) };
    return { ok: true, json: async () => ({ build: b }) };
  });
}

async function flush() {
  // let the awaited fetch/json promises inside tick() settle
  for (let k = 0; k < 4; k++) await Promise.resolve();
}

describe("fetchBuild", () => {
  it("returns the build id, and '' on a non-ok reply or a thrown fetch", async () => {
    expect(await fetchBuild(fakeFetch(["abc"]))).toBe("abc");
    expect(await fetchBuild(fakeFetch([""]))).toBe("");
    expect(await fetchBuild(fakeFetch([new Error("offline")]))).toBe("");
  });

  it("asks for /api/version with the cache bypassed", async () => {
    const f = fakeFetch(["abc"]);
    await fetchBuild(f);
    expect(f).toHaveBeenCalledWith("/api/version", { cache: "no-store" });
  });
});

describe("startVersionWatch", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("takes a baseline on the first success and reports the first change once, then stops", async () => {
    const onStale = vi.fn();
    const f = fakeFetch(["b1", "b1", "b2", "b3"]);
    startVersionWatch(onStale, { pollMs: 1000, fetchImpl: f });
    await flush();                                   // immediate tick → baseline b1
    expect(onStale).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1000);         // b1 again → nothing
    expect(onStale).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1000);         // b2 → stale
    expect(onStale).toHaveBeenCalledTimes(1);
    expect(onStale).toHaveBeenCalledWith("b2");
    const calls = f.mock.calls.length;
    await vi.advanceTimersByTimeAsync(5000);         // watch stopped: no more polling
    expect(f.mock.calls.length).toBe(calls);
    expect(onStale).toHaveBeenCalledTimes(1);
  });

  it("a server unreachable at load is still watched once it answers", async () => {
    const onStale = vi.fn();
    const f = fakeFetch([new Error("mid-restart"), "", "b1", "b2"]);
    startVersionWatch(onStale, { pollMs: 1000, fetchImpl: f });
    await flush();                                   // throw → ignored
    await vi.advanceTimersByTimeAsync(1000);         // non-ok → ignored
    await vi.advanceTimersByTimeAsync(1000);         // b1 → baseline
    expect(onStale).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1000);         // b2 → stale
    expect(onStale).toHaveBeenCalledWith("b2");
  });

  it("stop() ends the watch and a late reply does nothing", async () => {
    const onStale = vi.fn();
    const f = fakeFetch(["b1", "b2"]);
    const stop = startVersionWatch(onStale, { pollMs: 1000, fetchImpl: f });
    await flush();
    stop();
    await vi.advanceTimersByTimeAsync(3000);
    expect(onStale).not.toHaveBeenCalled();
    expect(f.mock.calls.length).toBe(1);
  });
});
