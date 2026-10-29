// seatSetupCommands: the Help page's one-liners follow the page origin (ported 2026-10-30).
import { describe, expect, it } from "vitest";

import { seatSetupCommands } from "../../src/lib/services/agentService.js";

describe("seatSetupCommands", () => {
  it("builds both one-liners from the origin it is given", () => {
    expect(seatSetupCommands("http://10.33.22.13:8000")).toEqual({
      windows: "irm http://10.33.22.13:8000/setup/setup.ps1 | iex",
      ubuntu: "curl -fsSL http://10.33.22.13:8000/setup/setup.sh | bash",
    });
  });

  it("follows whatever address the page was opened at, trailing slash or not", () => {
    expect(seatSetupCommands("http://localhost:8000/").windows).toBe("irm http://localhost:8000/setup/setup.ps1 | iex");
    expect(seatSetupCommands("http://terrenceb-dl.ws.atlnz.lc:8000").ubuntu).toBe(
      "curl -fsSL http://terrenceb-dl.ws.atlnz.lc:8000/setup/setup.sh | bash",
    );
  });

  it("never carries a typed-in address: the source has none", async () => {
    // jsdom gives import.meta.url an http: scheme, so resolve from the suite's root (vitest runs in svelte/).
    const fs = await import("node:fs");
    const path = await import("node:path");
    const src = fs.readFileSync(path.resolve(process.cwd(), "src/pages/HelpPage.svelte"), "utf-8");
    expect(src).not.toMatch(/https?:\/\/\d+\.\d+\.\d+\.\d+/);
  });

  describe.todo("the rest of agentService");
});
