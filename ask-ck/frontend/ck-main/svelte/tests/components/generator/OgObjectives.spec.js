import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/svelte";
import { scrollToBottom } from "../../../src/lib/utils/scroll.js";

import OgObjectives from "../../../src/lib/components/generator/OgObjectives.svelte";

// The scroll helpers call window.scrollTo / scrollIntoView, which jsdom does not implement —
// replaced with no-ops so they cannot fail a test.
vi.mock("../../../src/lib/utils/scroll.js", () => ({
  scrollToSection: vi.fn(),
  scrollToBottom: vi.fn(),
  scrollToTop: vi.fn(),
}));

// LlmButton (the "Synthesize Objectives (LLM)" button) starts a progress ticker that polls the
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

const summaryColumns = [
  { key: "source", label: "Source", width: 1 },
  { key: "id", label: "ID", width: 1 },
  { key: "title", label: "Title", width: 3 },
];

const summaryRows = [
  { id: "AWP-9208", source: "TestLink", title: "Private VLAN combination" },
  { id: "AWPTCM-T33247", source: "Zephyr", title: "IPv4_ARP - Clear ARP" },
];

// An objective as the server stores it: a <ul> with one <li> per objective.
const objective =
  "<ul>\n<li>Dynamic ARP entries are removed on clear</li>\n<li>Static ARP entries are kept</li>\n</ul>";

// The props the Generator page passes once a review step has chosen something.
const baseProps = {
  summaryColumns,
  summaryRows,
  chosenForObjectives: [summaryRows[0]],
};

function synthesizeButton() {
  return screen.getByRole("button", { name: "Synthesize Objectives (LLM)" });
}

function confirmButton() {
  return screen.getByRole("button", { name: "Review & Confirm" });
}

describe("OgObjectives", () => {
  describe("displays", () => {
    it("shows the summary rows", () => {
      render(OgObjectives, { props: baseProps });

      for (const row of summaryRows) {
        expect(screen.getByText(row.id)).toBeInTheDocument();
        expect(screen.getByText(row.title)).toBeInTheDocument();
      }
    });

    it("shows the summary without checkboxes, since nothing in it is selectable", () => {
      render(OgObjectives, { props: baseProps });

      expect(screen.queryByRole("checkbox")).toBe(null);
    });

    it.each([
      ["empty", ""],
      ["only whitespace", "   "],
    ])("hides the objective section when the objective is %s", (_, value) => {
      render(OgObjectives, { props: { ...baseProps, objective: value } });

      expect(screen.queryByText("Generated Objective")).toBe(null);
      expect(screen.queryByRole("button", { name: "Edit" })).toBe(null);
      expect(screen.queryByRole("button", { name: "Review & Confirm" })).toBe(null);
    });

    it("renders the objective's HTML as a list", () => {
      render(OgObjectives, { props: { ...baseProps, objective } });

      const items = screen.getAllByRole("listitem");
      expect(items).toHaveLength(2);
      expect(items[0]).toHaveTextContent("Dynamic ARP entries are removed on clear");
      expect(items[1]).toHaveTextContent("Static ARP entries are kept");
    });

    it("appears once the parent passes in an objective", async () => {
      const { rerender } = render(OgObjectives, { props: baseProps });
      expect(screen.queryByText("Generated Objective")).toBe(null);

      await rerender({ objective });

      expect(screen.getByText("Generated Objective")).toBeInTheDocument();
    });
  });

  // The LLM button, gated by a "No candidates selected" modal when nothing is chosen
  describe("synthesize", () => {
    it("calls onSynthesize straight away when candidates are chosen", async () => {
      const onSynthesize = vi.fn(async () => null);
      render(OgObjectives, { props: { ...baseProps, onSynthesize } });

      await fireEvent.click(synthesizeButton());

      await vi.waitFor(() => expect(onSynthesize).toHaveBeenCalledTimes(1));
      expect(onSynthesize).toHaveBeenCalledWith({ "X-CK-LLM-Call": "test-call-id" });
      expect(screen.queryByRole("dialog")).toBe(null); // no modal on the way
    });

    it("scrolls down to the objective once synthesis finishes", async () => {
      render(OgObjectives, {
        props: { ...baseProps, onSynthesize: vi.fn(async () => null) },
      });

      await fireEvent.click(synthesizeButton());

      await vi.waitFor(() => expect(scrollToBottom).toHaveBeenCalledTimes(1));
    });

    describe("with no candidates chosen", () => {
      const noneChosen = { ...baseProps, chosenForObjectives: [] };

      it("asks first, and does not call onSynthesize yet", async () => {
        const onSynthesize = vi.fn(async () => null);
        render(OgObjectives, { props: { ...noneChosen, onSynthesize } });

        await fireEvent.click(synthesizeButton());

        const dialog = await screen.findByRole("dialog");
        expect(within(dialog).getByText("No candidates selected")).toBeInTheDocument();
        expect(onSynthesize).not.toHaveBeenCalled();
      });

      it("runs onSynthesize after Continue", async () => {
        const onSynthesize = vi.fn(async () => null);
        render(OgObjectives, { props: { ...noneChosen, onSynthesize } });

        await fireEvent.click(synthesizeButton());
        const dialog = await screen.findByRole("dialog");
        await fireEvent.click(within(dialog).getByRole("button", { name: "Continue" }));

        await vi.waitFor(() => expect(onSynthesize).toHaveBeenCalledTimes(1));
        expect(screen.queryByRole("dialog")).toBe(null);
      });

      it("never runs onSynthesize after Cancel", async () => {
        const onSynthesize = vi.fn(async () => null);
        render(OgObjectives, { props: { ...noneChosen, onSynthesize } });

        await fireEvent.click(synthesizeButton());
        const dialog = await screen.findByRole("dialog");
        await fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));

        expect(screen.queryByRole("dialog")).toBe(null);
        expect(onSynthesize).not.toHaveBeenCalled();
        expect(synthesizeButton()).toBeEnabled(); // not left stuck "busy"
      });
    });
  });

  // Edit turns the <ul> into one line per objective; Save turns the lines back into a <ul>
  describe("editing", () => {
    async function startEditing(props = {}) {
      render(OgObjectives, { props: { ...baseProps, objective, ...props } });
      await fireEvent.click(screen.getByRole("button", { name: "Edit" }));
      return screen.getByRole("textbox");
    }

    it("opens a text box with one objective per line", async () => {
      const textbox = await startEditing();

      expect(textbox).toHaveValue(
        "Dynamic ARP entries are removed on clear\nStatic ARP entries are kept",
      );
    });

    it("keeps an objective with no <li> as a single line", async () => {
      const textbox = await startEditing({ objective: "<p>One plain objective</p>" });

      expect(textbox).toHaveValue("One plain objective");
    });

    it("hides Review & Confirm while editing", async () => {
      await startEditing();

      expect(screen.queryByRole("button", { name: "Review & Confirm" })).toBe(null);
    });

    it("saves the lines back as a <ul> and closes the editor", async () => {
      const onSaveObjective = vi.fn(async () => {});
      const textbox = await startEditing({ onSaveObjective });

      await fireEvent.input(textbox, { target: { value: "First objective\nSecond objective" } });
      await fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      expect(onSaveObjective).toHaveBeenCalledWith(
        "<ul>\n<li>First objective</li>\n<li>Second objective</li>\n</ul>",
      );
      await vi.waitFor(() => expect(screen.queryByRole("textbox")).toBe(null));
    });

    it("drops blank lines and trims each line", async () => {
      const onSaveObjective = vi.fn(async () => {});
      const textbox = await startEditing({ onSaveObjective });

      await fireEvent.input(textbox, { target: { value: "  First  \n\n   \nSecond" } });
      await fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      expect(onSaveObjective).toHaveBeenCalledWith(
        "<ul>\n<li>First</li>\n<li>Second</li>\n</ul>",
      );
    });

    it("escapes HTML the user typed, so it is shown as text", async () => {
      const onSaveObjective = vi.fn(async () => {});
      const textbox = await startEditing({ onSaveObjective });

      await fireEvent.input(textbox, { target: { value: "Port <1> & port <2>" } });
      await fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      expect(onSaveObjective).toHaveBeenCalledWith(
        "<ul>\n<li>Port &lt;1&gt; &amp; port &lt;2&gt;</li>\n</ul>",
      );
    });

    it("saves an empty string when every line is cleared", async () => {
      const onSaveObjective = vi.fn(async () => {});
      const textbox = await startEditing({ onSaveObjective });

      await fireEvent.input(textbox, { target: { value: "" } });
      await fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      expect(onSaveObjective).toHaveBeenCalledWith("");
    });

    it("Cancel throws the draft away without saving", async () => {
      const onSaveObjective = vi.fn(async () => {});
      const textbox = await startEditing({ onSaveObjective });

      await fireEvent.input(textbox, { target: { value: "Something else entirely" } });
      await fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

      expect(onSaveObjective).not.toHaveBeenCalled();
      expect(screen.queryByRole("textbox")).toBe(null);
      expect(
        screen.getByText("Dynamic ARP entries are removed on clear"),
      ).toBeInTheDocument(); // the original is still shown
    });

    it("shows an error and stays in the editor when saving fails", async () => {
      const onSaveObjective = vi.fn(async () => {
        throw new Error("disk full");
      });
      const textbox = await startEditing({ onSaveObjective });

      await fireEvent.input(textbox, { target: { value: "Kept objective" } });
      await fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));

      expect(await screen.findByText(/Save failed: disk full/)).toBeInTheDocument();
      expect(screen.getByRole("textbox")).toHaveValue("Kept objective"); // nothing typed is lost
    });
  });

  // "Review & Confirm" — onConfirm, its busy state, and its error banner
  describe("confirm", () => {
    it("calls onConfirm when clicked", async () => {
      const onConfirm = vi.fn(async () => {});
      render(OgObjectives, { props: { ...baseProps, objective, onConfirm } });

      await fireEvent.click(confirmButton());

      expect(onConfirm).toHaveBeenCalledTimes(1);
    });

    it("disables the button while onConfirm is running", async () => {
      // A promise the test resolves itself, so the call stays "running" until finish() is called.
      let finish;
      const onConfirm = vi.fn(() => new Promise((resolve) => (finish = resolve)));
      render(OgObjectives, { props: { ...baseProps, objective, onConfirm } });

      await fireEvent.click(confirmButton());
      expect(confirmButton()).toBeDisabled();

      finish();
      await vi.waitFor(() => expect(confirmButton()).toBeEnabled());
    });

    it("shows an error banner when onConfirm fails", async () => {
      const onConfirm = vi.fn(async () => {
        throw new Error("server said no");
      });
      render(OgObjectives, { props: { ...baseProps, objective, onConfirm } });

      await fireEvent.click(confirmButton());

      expect(await screen.findByText(/Confirm failed: server said no/)).toBeInTheDocument();
      expect(confirmButton()).toBeEnabled(); // the user can try again
    });

    it("does nothing when there is no onConfirm", async () => {
      render(OgObjectives, { props: { ...baseProps, objective } }); // onConfirm defaults to null

      await fireEvent.click(confirmButton());

      expect(confirmButton()).toBeEnabled();
      expect(screen.queryByText(/Confirm failed/)).toBe(null);
    });
  });
});
