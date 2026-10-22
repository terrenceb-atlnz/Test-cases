// Unit tests for src/lib/api/client.js — the seat LLM helpers, the per-tab session id, and the
// fetch patch that stamps our own /api/ requests with X-CK-Session / X-CK-LLM.
//
// Markers: "ADDED" = a test or block that was not here before; "CHANGED" = an existing test that
// was strengthened. Unmarked tests are as you wrote them.

// CHANGED: beforeEach, afterEach and vi are imported too — they worked before only because
// vitest.config.js sets `globals: true`.
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
    seatLlmHeaderValue,
    setEffectiveAuthMethod,
    effectiveAuthMethodActive,
    storedSeatLlm,
    SEAT_LLM_METHODS,
    SEAT_LLM_RETIRED_KEY,
 } from "../../src/lib/api/client.js";

const SEAT_KEY = 'draftingLLMConfig';

function storeSeat(cfg) {
    localStorage.setItem(SEAT_KEY, JSON.stringify(cfg));
}

beforeEach(() => {
    localStorage.clear();
    setEffectiveAuthMethod(null);
});

// ADDED: the constants other modules import — pinned so a typo or a dropped method is caught.
describe("constants", () => {

    it("lists exactly the two seat LLM methods", () => {
        expect(SEAT_LLM_METHODS).toEqual(['local_llm', 'claude_agent']);
    });

    it("names the localStorage key a retired method is recorded under", () => {
        expect(SEAT_LLM_RETIRED_KEY).toBe('ckSeatLlmRetired');
    });

});

describe("seatLlmHeaderValue", () => {

  it("joins a seat method and its three models with semicolons", () => {
    const cfg = {
      auth_method: "claude_agent",
      model: "opus",
      unit_model: "sonnet",
      match_model: "haiku",
    };
    expect(seatLlmHeaderValue(cfg)).toBe("claude_agent;opus;sonnet;haiku");
  });

  it("returns nothing when there is no config", () => {
    expect(seatLlmHeaderValue(null)).toBe("");
  });

  it("returns nothing when the config has no auth_method", () => {
    expect(seatLlmHeaderValue({ model: "opus" })).toBe("");
  });

  it("returns nothing for a method that is not a seat LLM", () => {
    const cfg = {
      auth_method: "api_key",
      model: "x",
      unit_model: "unit_model",
      match_model: "y",
    };
    expect(seatLlmHeaderValue(cfg)).toBe("");
  });

  it("accepts a seat method in any case and keeps its spelling", () => {
    const cfg = { auth_method: "CLAUDE_AGENT", model: "opus", unit_model: "sonnet", match_model: "haiku" };
    expect(seatLlmHeaderValue(cfg)).toBe("CLAUDE_AGENT;opus;sonnet;haiku");
  });

  it("leaves an empty slot for each missing model", () => {
    expect(seatLlmHeaderValue({ auth_method: "claude_agent", model: "opus" })).toBe("claude_agent;opus;;");
    expect(seatLlmHeaderValue({ auth_method: "local_llm", model: null, unit_model: undefined, match_model: "m" }))
      .toBe("local_llm;;;m");
  });

  it("strips ; and newlines so a value cannot split the header", () => {
    const cfg = {
      auth_method: "claude_agent",
      model: "op;us\n",
      unit_model: "sonnet",
      match_model: "haiku",
    };
    expect(seatLlmHeaderValue(cfg)).toBe("claude_agent;opus;sonnet;haiku");
  });

  it("strips carriage returns, in every field", () => {
    const cfg = { auth_method: "claude_agent", model: "a\r\nb", unit_model: "c;d", match_model: "e\rf" };
    expect(seatLlmHeaderValue(cfg)).toBe("claude_agent;ab;cd;ef");
  });

  it("turns non-string model values into text", () => {
    expect(seatLlmHeaderValue({ auth_method: "local_llm", model: 7, unit_model: false, match_model: 0 }))
      .toBe("local_llm;7;false;0");
  });

});

describe("setEffectiveAuthMethod", () => {

    it("sets effectiveAuthMethod to method value", () => {

        setEffectiveAuthMethod('claude_agent');
        expect(effectiveAuthMethodActive('claude_agent')).toBe(true);
        expect(effectiveAuthMethodActive('local_llm')).toBe(false);

        setEffectiveAuthMethod('local_llm');
        expect(effectiveAuthMethodActive('claude_agent')).toBe(false);
        expect(effectiveAuthMethodActive('local_llm')).toBe(true);
    });

    it("sets effectiveAuthMethod with no value", () => {

        setEffectiveAuthMethod('claude_agent');
        expect(effectiveAuthMethodActive('claude_agent')).toBe(true);

        setEffectiveAuthMethod();
        expect(effectiveAuthMethodActive('claude_agent')).toBe(false);
        expect(effectiveAuthMethodActive(null)).toBe(true);
    });

    it("treats an empty string or null as no value", () => {

        setEffectiveAuthMethod('claude_agent');
        setEffectiveAuthMethod('');
        expect(effectiveAuthMethodActive('claude_agent')).toBe(false);
        expect(effectiveAuthMethodActive(null)).toBe(true);

        setEffectiveAuthMethod('claude_agent');
        setEffectiveAuthMethod(null);
        expect(effectiveAuthMethodActive(null)).toBe(true);
    });

});

describe("effectiveAuthMethodActive", () => {

    it("returns whether the method matches the stored seat's auth_method, over the session value", () => {

        setEffectiveAuthMethod('claude_agent');
        storeSeat({auth_method: 'local_llm'})
        expect(effectiveAuthMethodActive('local_llm')).toBe(true);
        expect(effectiveAuthMethodActive('claude_agent')).toBe(false);

        setEffectiveAuthMethod('local_llm');
        storeSeat({auth_method: 'claude_agent'})
        expect(effectiveAuthMethodActive('local_llm')).toBe(false);
        expect(effectiveAuthMethodActive('claude_agent')).toBe(true);
    });

    it("falls back to the session value when no seat is stored", () => {

        setEffectiveAuthMethod('claude_agent');
        expect(effectiveAuthMethodActive('claude_agent')).toBe(true);
        expect(effectiveAuthMethodActive('local_llm')).toBe(false);

        setEffectiveAuthMethod(null);
        expect(effectiveAuthMethodActive('local_llm')).toBe(false);
        expect(effectiveAuthMethodActive('claude_agent')).toBe(false);
        expect(effectiveAuthMethodActive(null)).toBe(true);
    });

    it("falls back to the session value when the stored seat has no auth_method", () => {

        setEffectiveAuthMethod('local_llm');
        storeSeat({auth_method: null})
        expect(effectiveAuthMethodActive('local_llm')).toBe(true);
        expect(effectiveAuthMethodActive('claude_agent')).toBe(false);
    });

    it("falls back to the session value when the stored seat uses a retired method", () => {

        setEffectiveAuthMethod('claude_agent');
        storeSeat({auth_method: 'api_key'})
        expect(effectiveAuthMethodActive('claude_agent')).toBe(true);
        expect(effectiveAuthMethodActive('api_key')).toBe(false);
    });
});

describe("storedSeatLlm", () => {

    it("returns null when nothing is stored", () => {
        expect(storedSeatLlm()).toBe(null);
    });

    it("returns the stored config when it uses a seat method", () => {
        const cfg = { auth_method: 'claude_agent', model: 'opus', unit_model: 'sonnet', match_model: 'haiku' };
        storeSeat(cfg);
        expect(storedSeatLlm()).toEqual(cfg);
    });

    it("keeps a seat method written in capitals", () => {
        storeSeat({ auth_method: 'LOCAL_LLM' });
        expect(storedSeatLlm()).toEqual({ auth_method: 'LOCAL_LLM' });
        expect(localStorage.getItem(SEAT_KEY)).not.toBe(null);
    });

    it("returns a config that has no auth_method unchanged", () => {
        storeSeat({ model: 'opus' });
        expect(storedSeatLlm()).toEqual({ model: 'opus' });
    });

    it("retires a config whose method is no longer a seat method", () => {
        storeSeat({ auth_method: 'api_key', model: 'x' });

        expect(storedSeatLlm()).toBe(null);
        expect(localStorage.getItem(SEAT_KEY)).toBe(null);
        expect(localStorage.getItem(SEAT_LLM_RETIRED_KEY)).toBe('api_key');
    });

    it("returns null on the next read after retiring", () => {
        storeSeat({ auth_method: 'api_key' });
        storedSeatLlm();

        expect(storedSeatLlm()).toBe(null);
        expect(localStorage.getItem(SEAT_LLM_RETIRED_KEY)).toBe('api_key');
    });

    it("returns null instead of throwing when the stored value is not JSON", () => {
        localStorage.setItem(SEAT_KEY, '{not json');
        expect(() => storedSeatLlm()).not.toThrow();
        expect(storedSeatLlm()).toBe(null);
    });

    it("returns null when localStorage cannot be read", () => {
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
        expect(storedSeatLlm()).toBe(null);
    });

});

describe("on import", () => {

    let realFetch;
    let fakeFetch;

    // Install a fake fetch that records its calls, then import a fresh client.js on top of it.
    async function loadClient() {
        fakeFetch = vi.fn(() => Promise.resolve(new Response('{}')));
        window.fetch = fakeFetch;
        vi.resetModules();
        return import("../../src/lib/api/client.js");
    }

    // The headers the patched fetch passed on to the fake, for its most recent call.
    function sentHeaders() {
        const init = fakeFetch.mock.calls.at(-1)[1];
        return new Headers(init && init.headers);
    }

    beforeEach(() => {
        realFetch = window.fetch;
        sessionStorage.clear();
    });

    afterEach(() => {
        window.fetch = realFetch;
    });

    // --- CK_SESSION_ID ------------------------------------------------------------------

    // A new tab: an id is made, shaped sess-<random>-<time>, and saved for the tab.
    it("creates a session id and keeps it in sessionStorage", async () => {
        const { CK_SESSION_ID } = await loadClient();

        expect(CK_SESSION_ID).toMatch(/^sess-[a-z0-9]+-[a-z0-9]+$/);
        expect(sessionStorage.getItem('ckSessionId')).toBe(CK_SESSION_ID);
    });

    // A reload in the same tab: the saved id is reused, not replaced.
    it("reuses the session id already in sessionStorage", async () => {
        sessionStorage.setItem('ckSessionId', 'sess-existing-1');
        const { CK_SESSION_ID } = await loadClient();

        expect(CK_SESSION_ID).toBe('sess-existing-1');
    });

    // --- The fetch patch ------------------------------------------------------------------

    // Our own API always gets the session header.
    it("adds X-CK-Session to a request to /api/", async () => {
        const { CK_SESSION_ID } = await loadClient();
        await window.fetch('/api/llm_config');

        expect(sentHeaders().get('X-CK-Session')).toBe(CK_SESSION_ID);
    });

    // A full URL on this page's own host counts as our API too.
    it("adds the headers to a full URL on this page's host", async () => {
        await loadClient();
        await window.fetch(`http://${location.host}/api/llm_config`);

        expect(sentHeaders().get('X-CK-Session')).toBeTruthy();
    });

    // With a seat method stored, X-CK-LLM carries seatLlmHeaderValue's string.
    it("adds X-CK-LLM when a seat method is stored", async () => {
        storeSeat({ auth_method: 'claude_agent', model: 'opus', unit_model: 'sonnet', match_model: 'haiku' });
        await loadClient();
        await window.fetch('/api/pytest-create/step_prompts');

        expect(sentHeaders().get('X-CK-LLM')).toBe('claude_agent;opus;sonnet;haiku');
    });

    // No seat stored: the session header only, no X-CK-LLM.
    it("leaves X-CK-LLM off when no seat is stored", async () => {
        await loadClient();
        await window.fetch('/api/llm_config');

        expect(sentHeaders().get('X-CK-LLM')).toBe(null);
    });

    // The seat is read on EVERY request, not once at import — a choice made later still applies.
    it("reads the seat at request time, not import time", async () => {
        await loadClient();
        storeSeat({ auth_method: 'local_llm', model: 'm' });
        await window.fetch('/api/llm_config');

        expect(sentHeaders().get('X-CK-LLM')).toBe('local_llm;m;;');
    });

    // The caller's own headers survive alongside the added ones.
    it("keeps the caller's own headers", async () => {
        await loadClient();
        await window.fetch('/api/save', { method: 'POST', headers: { 'Content-Type': 'application/json' } });

        const h = sentHeaders();
        expect(h.get('Content-Type')).toBe('application/json');
        expect(h.get('X-CK-Session')).toBeTruthy();
        expect(fakeFetch.mock.calls.at(-1)[1].method).toBe('POST');
    });

    // The seat agent and any other host get NOTHING added — the session id must not leak.
    it("does not touch requests to the local ck-agent or other hosts", async () => {
        storeSeat({ auth_method: 'claude_agent' });
        await loadClient();

        await window.fetch('http://127.0.0.1:8765/health');
        expect(fakeFetch.mock.calls.at(-1)[1]).toBeUndefined();

        await window.fetch('https://example.com/api/thing');
        expect(fakeFetch.mock.calls.at(-1)[1]).toBeUndefined();
    });

    // A Request object (not a string) is recognised by its .url, and its own headers are kept.
    it("handles a Request object, keeping its headers", async () => {
        await loadClient();
        const req = new Request(`http://${location.host}/api/llm_config`, { headers: { 'X-Test': 'yes' } });
        await window.fetch(req);

        const h = sentHeaders();
        expect(h.get('X-CK-Session')).toBeTruthy();
        expect(h.get('X-Test')).toBe('yes');
    });

    // The patch passes the call straight through and returns the real fetch's response.
    it("returns the underlying fetch's response", async () => {
        await loadClient();
        const res = await window.fetch('/api/llm_config');

        expect(await res.text()).toBe('{}');
        expect(fakeFetch).toHaveBeenCalledTimes(1);
    });

    // "Never break fetch": if building the headers throws, the request still goes out.
    it("still sends the request if adding the headers fails", async () => {
        await loadClient();
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });

        await expect(window.fetch('/api/llm_config')).resolves.toBeTruthy();
        expect(fakeFetch).toHaveBeenCalledTimes(1);
    });

});
