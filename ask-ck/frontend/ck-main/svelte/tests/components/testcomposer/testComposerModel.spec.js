// deepLink / tabForRun: the deep-link contract the server writes and Classic reads
// (current/test-composer/test-composer.js), ported into this app 2026-10-30 (PLAN-svelte-cutover D7).
import { describe, expect, it } from "vitest";

import { deepLink, tabForRun } from "../../../src/lib/components/testcomposer/testComposerModel.js";

describe("tabForRun", () => {
  it("routes a run id by the kind baked into it", () => {
    expect(tabForRun("2026-10-13T1223-val-3ede")).toBe("validate");
    expect(tabForRun("2026-10-16T0900-scr-ab12")).toBe("run");
    expect(tabForRun("2026-10-13T1454-tc-43dd")).toBe("compose");
  });
});

describe("deepLink", () => {
  it("Finalize's Zephyr link opens Compose on that script", () => {
    expect(deepLink("?panel=composer&script=9002_IPv4/test-9002.33241.py")).toEqual({
      tab: "compose",
      preselect: "9002_IPv4/test-9002.33241.py",
      openRun: null,
    });
  });

  it("a validation link opens Validate on that script", () => {
    expect(deepLink("?panel=validation&script=9001_Port/test-9001.33235.py")).toEqual({
      tab: "validate",
      preselect: "9001_Port/test-9001.33235.py",
      openRun: null,
    });
  });

  it("the run e-mail's link opens the run on the tab its id belongs to", () => {
    expect(deepLink("?panel=tc-runs&run=2026-10-13T1223-val-3ede")).toEqual({
      tab: "validate",
      preselect: null,
      openRun: "2026-10-13T1223-val-3ede",
    });
    expect(deepLink("?panel=tc-runs&run=2026-10-16T0900-scr-ab12").tab).toBe("run");
    expect(deepLink("?panel=tc-runs&run=2026-10-13T1454-tc-43dd").tab).toBe("compose");
  });

  it("a run-scripts share link opens the Run Scripts tab", () => {
    expect(deepLink("?panel=run-scripts&source=generated&scripts=a.py,b.py").tab).toBe("run");
  });

  it("the path form works on /composer only", () => {
    expect(deepLink("?script=9002_IPv4/x.py", "/composer")).toEqual({
      tab: "compose",
      preselect: "9002_IPv4/x.py",
      openRun: null,
    });
    expect(deepLink("?run=2026-10-13T1223-val-3ede", "/composer/").tab).toBe("validate");
    expect(deepLink("?script=9002_IPv4/x.py", "/generator")).toBeNull();
  });

  it("ignores URLs that carry no deep link", () => {
    expect(deepLink("")).toBeNull();
    expect(deepLink("?panel=tc-runs")).toBeNull();
    expect(deepLink("?panel=nope&script=x.py")).toBeNull();
    expect(deepLink("?foo=bar", "/composer")).toBeNull();
  });
});
