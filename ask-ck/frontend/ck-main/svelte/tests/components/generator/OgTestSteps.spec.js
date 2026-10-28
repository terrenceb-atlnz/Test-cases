import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/svelte";
import { scrollToBottom } from "../../../src/lib/utils/scroll.js";

import OgTestSteps from "../../../src/lib/components/generator/OgTestSteps.svelte";

// The scroll helpers call window.scrollTo / scrollIntoView, which jsdom does not implement —
// replaced with no-ops so they cannot fail a test.
vi.mock("../../../src/lib/utils/scroll.js", () => ({
  scrollToSection: vi.fn(),
  scrollToBottom: vi.fn(),
  scrollToTop: vi.fn(),
}));

// LlmButton (the "Synthesize Test Steps (LLM)" button) starts a progress ticker that polls the
// server and fetches token usage afterwards. There is no server in a test, so those two are
// replaced; the rest of the module stays real.
vi.mock("../../../src/lib/services/llmProgressService.js", async (importOriginal) => ({
  ...(await importOriginal()),
  startLlmProgress: vi.fn(() => ({
    callId: "test-call-id",
    headers: { "X-CK-LLM-Call": "test-call-id" },
    stop: vi.fn(),
  })),
  fetchLatestLlmUsage: vi.fn(async () => null),
}));

const objective =
  "<ul>\n<li>Dynamic ARP entries are removed on clear</li>\n<li>Static ARP entries are kept</li>\n</ul>";

const steps = [
  { description: "Note: Related ART Tests linked in Traceability.", expectedResult: "" },
  { description: "Populate the ARP cache with dynamic entries", expectedResult: "show arp lists them" },
  { description: "Clear the ARP cache", expectedResult: "Dynamic entries are gone" },
];

// The props the Generator page passes once steps have been synthesized.
const baseProps = {
  caseKey: "AWPTCM-T33247",
  caseTitle: "(19) IPv4_ARP - Clear ARP",
  objective,
  steps,
};

function button(name) {
  return screen.getByRole("button", { name });
}

describe("OgTestSteps", () => {
  describe("displays", () => {
    it("renders the objective's HTML", () => {
      render(OgTestSteps, { props: baseProps });

      expect(screen.getByText("Dynamic ARP entries are removed on clear")).toBeInTheDocument();
      expect(screen.getByText("Static ARP entries are kept")).toBeInTheDocument();
    });

    it("says so when there is no objective", () => {
      render(OgTestSteps, { props: { ...baseProps, objective: "" } });

      expect(screen.getByText("No objective on session.")).toBeInTheDocument();
    });

    it("lists each step in order, with its expected result when it has one", () => {
      render(OgTestSteps, { props: baseProps });

      const items = screen.getAllByRole("listitem").filter((li) => li.closest(".steps-list"));
      expect(items).toHaveLength(3);
      expect(items[1]).toHaveTextContent("Populate the ARP cache with dynamic entries");
      expect(items[1]).toHaveTextContent("Expected: show arp lists them");
      expect(items[0]).not.toHaveTextContent("Expected:"); // empty expectedResult → no line
    });

    it("hides the steps, export and push sections until there are steps", () => {
      render(OgTestSteps, { props: { ...baseProps, steps: [] } });

      expect(screen.queryByText("Generated Test Steps")).toBe(null);
      expect(screen.queryByRole("button", { name: "Export Repeatable Bundle" })).toBe(null);
      expect(screen.queryByRole("button", { name: "Push to Zephyr" })).toBe(null);
    });

    it("shows the steps once the parent passes them in", async () => {
      const { rerender } = render(OgTestSteps, { props: { ...baseProps, steps: [] } });

      await rerender({ steps });

      expect(screen.getByText("Generated Test Steps")).toBeInTheDocument();
      expect(screen.getByText("Clear the ARP cache")).toBeInTheDocument();
    });
  });

  describe("synthesize", () => {
    it("is disabled, and not an LLM button, when there is no objective", () => {
      render(OgTestSteps, { props: { ...baseProps, objective: "" } });

      expect(button("Synthesize Test Steps")).toBeDisabled();
      expect(screen.queryByRole("button", { name: "Synthesize Test Steps (LLM)" })).toBe(null);
    });

    it("calls onSynthesize with the LLM call headers", async () => {
      const onSynthesize = vi.fn(async () => null);
      render(OgTestSteps, { props: { ...baseProps, onSynthesize } });

      await fireEvent.click(button("Synthesize Test Steps (LLM)"));

      await vi.waitFor(() => expect(onSynthesize).toHaveBeenCalledTimes(1));
      expect(onSynthesize).toHaveBeenCalledWith({ "X-CK-LLM-Call": "test-call-id" });
    });

    it("scrolls down to the steps once synthesis finishes", async () => {
      render(OgTestSteps, { props: { ...baseProps, onSynthesize: vi.fn(async () => null) } });

      await fireEvent.click(button("Synthesize Test Steps (LLM)"));

      await vi.waitFor(() => expect(scrollToBottom).toHaveBeenCalledTimes(1));
    });
  });

  // Edit works on a copy of the steps; only Save Changes sends them to the parent
  describe("editing", () => {
    async function startEditing(props = {}) {
      render(OgTestSteps, { props: { ...baseProps, ...props } });
      await fireEvent.click(button("Edit"));
    }

    const descriptions = () => screen.getAllByPlaceholderText("Step description");
    const expecteds = () => screen.getAllByPlaceholderText("Expected result (optional)");

    it("opens a pair of fields per step, filled with the current text", async () => {
      await startEditing();

      expect(descriptions()).toHaveLength(3);
      expect(descriptions()[2]).toHaveValue("Clear the ARP cache");
      expect(expecteds()[2]).toHaveValue("Dynamic entries are gone");
    });

    it("+ Add step adds an empty pair of fields at the end", async () => {
      await startEditing();

      await fireEvent.click(button("+ Add step"));

      expect(descriptions()).toHaveLength(4);
      expect(descriptions()[3]).toHaveValue("");
    });

    it("the trash button removes that step only", async () => {
      await startEditing();

      await fireEvent.click(screen.getAllByRole("button", { name: "Remove step" })[1]);

      expect(descriptions()).toHaveLength(2);
      expect(descriptions().map((d) => d.value)).toEqual([
        steps[0].description,
        steps[2].description,
      ]);
    });

    it("saves the edited steps, trimmed, and closes the editor", async () => {
      const onSaveSteps = vi.fn(async () => {});
      await startEditing({ onSaveSteps });

      await fireEvent.input(descriptions()[2], { target: { value: "  Clear all ARP entries  " } });
      await fireEvent.input(expecteds()[2], { target: { value: " Cache is empty " } });
      await fireEvent.click(button("Save Changes"));

      expect(onSaveSteps).toHaveBeenCalledWith([
        { description: steps[0].description, expectedResult: "" },
        { description: steps[1].description, expectedResult: steps[1].expectedResult },
        { description: "Clear all ARP entries", expectedResult: "Cache is empty" },
      ]);
      await vi.waitFor(() =>
        expect(screen.queryByPlaceholderText("Step description")).toBe(null),
      );
    });

    it("Cancel throws the edits away without saving", async () => {
      const onSaveSteps = vi.fn(async () => {});
      await startEditing({ onSaveSteps });

      await fireEvent.input(descriptions()[0], { target: { value: "Something else" } });
      await fireEvent.click(button("+ Add step"));
      await fireEvent.click(button("Cancel"));

      expect(onSaveSteps).not.toHaveBeenCalled();
      expect(screen.getAllByRole("listitem").filter((li) => li.closest(".steps-list"))).toHaveLength(3);
      expect(screen.getByText(steps[0].description)).toBeInTheDocument(); // the original is shown
    });

    it("starts from the saved steps again after a Cancel", async () => {
      await startEditing();

      await fireEvent.input(descriptions()[0], { target: { value: "Something else" } });
      await fireEvent.click(button("Cancel"));
      await fireEvent.click(button("Edit"));

      expect(descriptions()[0]).toHaveValue(steps[0].description);
    });

    it("shows an error and stays in the editor when saving fails", async () => {
      const onSaveSteps = vi.fn(async () => {
        throw new Error("disk full");
      });
      await startEditing({ onSaveSteps });

      await fireEvent.input(descriptions()[0], { target: { value: "Kept edit" } });
      await fireEvent.click(button("Save Changes"));

      expect(await screen.findByText(/Save failed: disk full/)).toBeInTheDocument();
      expect(descriptions()[0]).toHaveValue("Kept edit"); // nothing typed is lost
    });
  });

  // Success is read from the response body: the server can answer 200 with wrote_bundle: false
  describe("export", () => {
    async function exportWith(result, props = {}) {
      const onExport = vi.fn(async () => {
        if (result instanceof Error) throw result;
        return result;
      });
      render(OgTestSteps, { props: { ...baseProps, onExport, ...props } });
      await fireEvent.click(button("Export Repeatable Bundle"));
      return onExport;
    }

    it("shows where the bundle was saved, and calls onFinished", async () => {
      const onFinished = vi.fn();
      await exportWith(
        { wrote_bundle: true, saved_to: "exports/AWPTCM-T33247", saved_files: ["steps.json", "traceability.md"] },
        { onFinished },
      );

      const dialog = await screen.findByRole("dialog", { name: "Export successful" });
      expect(
        within(dialog).getByText("Saved to exports/AWPTCM-T33247/ (steps.json, traceability.md)."),
      ).toBeInTheDocument();
      expect(within(dialog).getByText(baseProps.caseTitle)).toBeInTheDocument();
      expect(onFinished).toHaveBeenCalledTimes(1);
    });

    it("adds advisory warnings to the success message", async () => {
      await exportWith({
        saved_to: "exports/X",
        saved_files: ["steps.json"],
        validation: { warnings: ["step 3 is long", "no expected result on step 1"] },
      });

      const dialog = await screen.findByRole("dialog", { name: "Export successful" });
      expect(
        within(dialog).getByText(/Advisory warnings: step 3 is long; no expected result on step 1/),
      ).toBeInTheDocument();
    });

    it("reports 'Export blocked' when the server refuses to write, without calling onFinished", async () => {
      const onFinished = vi.fn();
      await exportWith(
        {
          wrote_bundle: false,
          message: "Bundle failed validation\nmore detail on the next line",
          validation: { issues: ["step 2 is empty", "objective missing"] },
        },
        { onFinished },
      );

      const dialog = await screen.findByRole("dialog", { name: "Export blocked" });
      expect(
        within(dialog).getByText(
          "Bundle failed validation Issues: step 2 is empty; objective missing",
        ),
      ).toBeInTheDocument(); // only the message's first line is used
      expect(onFinished).not.toHaveBeenCalled();
    });

    it("uses a default headline when a blocked export has no message", async () => {
      await exportWith({ wrote_bundle: false });

      const dialog = await screen.findByRole("dialog", { name: "Export blocked" });
      expect(within(dialog).getByText("Export blocked — no bundle written.")).toBeInTheDocument();
    });

    it("reports 'Export failed' when onExport throws", async () => {
      const onFinished = vi.fn();
      await exportWith(new Error("connection reset"), { onFinished });

      const dialog = await screen.findByRole("dialog", { name: "Export failed" });
      expect(within(dialog).getByText("connection reset")).toBeInTheDocument();
      expect(onFinished).not.toHaveBeenCalled();
    });

    it("Close dismisses the result", async () => {
      await exportWith({ saved_to: "exports/X", saved_files: [] });

      const dialog = await screen.findByRole("dialog", { name: "Export successful" });
      await fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));

      expect(screen.queryByRole("dialog")).toBe(null);
    });
  });

  // Preview is a dry run; the real push writes to the LIVE Zephyr server, so it is confirmed first
  describe("push to Zephyr", () => {
    const output = () => document.querySelector(".push-output");

    it("Preview runs a dry run and shows its output", async () => {
      const onPushToZephyr = vi.fn(async () => ({ ok: true, output: "would create version 2.0" }));
      render(OgTestSteps, { props: { ...baseProps, onPushToZephyr } });

      await fireEvent.click(button("Preview Push (dry-run)"));

      expect(onPushToZephyr).toHaveBeenCalledWith({ dryRun: true });
      await vi.waitFor(() =>
        expect(output()).toHaveTextContent(
          "Dry-run preview (no changes made): would create version 2.0",
        ),
      );
    });

    it("Preview flags a run that reported problems, with its exit code", async () => {
      render(OgTestSteps, {
        props: {
          ...baseProps,
          onPushToZephyr: vi.fn(async () => ({ ok: false, returncode: 2, output: "JIRA_KEY missing" })),
        },
      });

      await fireEvent.click(button("Preview Push (dry-run)"));

      await vi.waitFor(() =>
        expect(output()).toHaveTextContent("⚠ Push preview reported problems (exit 2)"),
      );
      expect(output()).toHaveTextContent("JIRA_KEY missing");
    });

    it("Preview shows the error when onPushToZephyr throws", async () => {
      render(OgTestSteps, {
        props: { ...baseProps, onPushToZephyr: vi.fn(async () => { throw new Error("timeout"); }) },
      });

      await fireEvent.click(button("Preview Push (dry-run)"));

      await vi.waitFor(() => expect(output()).toHaveTextContent("Push preview failed: timeout"));
    });

    it("Push to Zephyr asks first, naming the case, and pushes nothing yet", async () => {
      const onPushToZephyr = vi.fn(async () => ({ ok: true }));
      render(OgTestSteps, { props: { ...baseProps, onPushToZephyr } });

      await fireEvent.click(button("Push to Zephyr"));

      const dialog = await screen.findByRole("dialog", { name: "Push to the LIVE Zephyr server?" });
      expect(
        within(dialog).getByText(/Push AWPTCM-T33247 to the LIVE Zephyr server\?/),
      ).toBeInTheDocument();
      expect(onPushToZephyr).not.toHaveBeenCalled();
    });

    it("Cancel in the confirmation pushes nothing", async () => {
      const onPushToZephyr = vi.fn(async () => ({ ok: true }));
      render(OgTestSteps, { props: { ...baseProps, onPushToZephyr } });

      await fireEvent.click(button("Push to Zephyr"));
      const dialog = await screen.findByRole("dialog");
      await fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));

      expect(screen.queryByRole("dialog")).toBe(null);
      expect(onPushToZephyr).not.toHaveBeenCalled();
    });

    it("Push in the confirmation runs the real push and shows its output", async () => {
      const onPushToZephyr = vi.fn(async () => ({ ok: true, output: "created version 2.0" }));
      render(OgTestSteps, { props: { ...baseProps, onPushToZephyr } });

      await fireEvent.click(button("Push to Zephyr"));
      const dialog = await screen.findByRole("dialog");
      await fireEvent.click(within(dialog).getByRole("button", { name: "Push" }));

      expect(onPushToZephyr).toHaveBeenCalledWith({ dryRun: false });
      await vi.waitFor(() =>
        expect(output()).toHaveTextContent("✓ Push complete: created version 2.0"),
      );
    });

    it("a failed real push says FAILED with its exit code", async () => {
      render(OgTestSteps, {
        props: {
          ...baseProps,
          onPushToZephyr: vi.fn(async () => ({ ok: false, returncode: 1, output: "401 Unauthorized" })),
        },
      });

      await fireEvent.click(button("Push to Zephyr"));
      const dialog = await screen.findByRole("dialog");
      await fireEvent.click(within(dialog).getByRole("button", { name: "Push" }));

      await vi.waitFor(() => expect(output()).toHaveTextContent("⚠ Push FAILED (exit 1)"));
      expect(output()).toHaveTextContent("401 Unauthorized");
    });
  });
});
