// selectForCopy: "copy" buttons select the text for a manual Ctrl+C — no clipboard write on plain http.
import { afterEach, describe, expect, it } from "vitest";

import { SELECTED_HINT, selectForCopy } from "../../src/lib/utils/select.js";

afterEach(() => {
  document.body.innerHTML = "";
  window.getSelection()?.removeAllRanges();
});

describe("selectForCopy", () => {
  it("selects an input's whole value", () => {
    const input = document.createElement("input");
    input.value = "irm http://10.33.22.13:8000/setup/setup.ps1 | iex";
    document.body.appendChild(input);
    expect(selectForCopy(input)).toBe(true);
    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe(input.value.length);
    expect(document.activeElement).toBe(input);
  });

  it("selects an element's text content by range", () => {
    const box = document.createElement("div");
    box.textContent = "curl -fsSL http://10.33.22.13:8000/setup/setup.sh | bash";
    document.body.appendChild(box);
    expect(selectForCopy(box)).toBe(true);
    expect(window.getSelection().toString()).toBe(box.textContent);
  });

  it("replaces an earlier selection rather than adding to it", () => {
    const a = document.createElement("div");
    a.textContent = "first";
    const b = document.createElement("div");
    b.textContent = "second";
    document.body.append(a, b);
    selectForCopy(a);
    selectForCopy(b);
    expect(window.getSelection().toString()).toBe("second");
  });

  it("returns false when there is nothing to select", () => {
    expect(selectForCopy(null)).toBe(false);
    expect(selectForCopy(undefined)).toBe(false);
  });

  it("the hint tells the user what to press", () => {
    expect(SELECTED_HINT).toMatch(/Ctrl\+C/);
  });
});
