// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { Agents } from "./agents";
import { WritingLibrary } from "./writing-library";
import { DraftsPage } from "./drafts-page";
import { call } from "./engine";
import { navigateSafely, useUnsavedChanges } from "./unsaved-changes";
vi.mock("./engine", async (original) => ({
  ...(await original<typeof import("./engine")>()),
  call: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

const assistants = [
  {
    id: "one",
    name: "News editor",
    instructions: "Explain the source",
    profile_id: "p",
    model_id: "m",
  },
  {
    id: "two",
    name: "Writing partner",
    instructions: "Write clearly",
    profile_id: "p",
    model_id: "m",
  },
];
it("protects assistant edits during selection and requires confirmation before deletion", async () => {
  vi.mocked(call).mockImplementation(async (command) =>
    command === "agents.list"
      ? { agents: assistants }
      : { models: [{ id: "m" }] },
  );
  render(
    <Agents
      snapshot={{ profiles: [{ id: "p", label: "Local account" }] }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(await screen.findByRole("button", { name: /News editor/ }));
  fireEvent.change(
    screen.getByRole("textbox", { name: "Assistant instructions" }),
    { target: { value: "Unsaved improvements" } },
  );
  fireEvent.click(screen.getByRole("button", { name: /Writing partner/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Keep editing" }));
  expect(
    (
      screen.getByRole("textbox", {
        name: "Assistant instructions",
      }) as HTMLTextAreaElement
    ).value,
  ).toBe("Unsaved improvements");
  fireEvent.click(screen.getByRole("button", { name: "Delete assistant" }));
  expect(call).not.toHaveBeenCalledWith("agents.delete", expect.anything());
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  fireEvent.click(screen.getByRole("button", { name: "Delete assistant" }));
  fireEvent.click(
    screen.getAllByRole("button", { name: "Delete assistant" }).at(-1)!,
  );
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("agents.delete", { agent_id: "one" }),
  );
  expect(screen.queryByRole("button", { name: /News editor/ })).toBeNull();
});

it("retains new reference text after a failed save and protects navigation", async () => {
  const error = vi.fn(),
    leave = vi.fn();
  vi.mocked(call).mockRejectedValue(new Error("Disk unavailable"));
  render(
    <WritingLibrary
      snapshot={{ sources: [] }}
      refresh={async () => {}}
      onError={error}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Add writing" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Title" }), {
    target: { value: "My writing" },
  });
  fireEvent.change(screen.getByRole("textbox", { name: "Writing text" }), {
    target: { value: "Keep this reference" },
  });
  act(() => navigateSafely(leave));
  fireEvent.click(screen.getByRole("button", { name: "Save and continue" }));
  await waitFor(() =>
    expect(error).toHaveBeenCalledWith("Error: Disk unavailable"),
  );
  expect(leave).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Keep editing" }));
  expect(
    (
      screen.getByRole("textbox", {
        name: "Writing text",
      }) as HTMLTextAreaElement
    ).value,
  ).toBe("Keep this reference");
});

it("does not let an old reference response replace the latest selection", async () => {
  let finishOld: (value: unknown) => void = () => {};
  vi.mocked(call).mockImplementation(async (_command, payload) =>
    payload?.item_id === "old"
      ? new Promise((resolve) => {
          finishOld = resolve;
        })
      : { text: "Latest reference content" },
  );
  render(
    <WritingLibrary
      snapshot={{
        sources: [
          { id: "old", title: "Old note" },
          { id: "new", title: "Current note" },
        ],
      }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: /Old note/ }));
  fireEvent.click(screen.getByRole("button", { name: /Current note/ }));
  await screen.findByText("Latest reference content");
  await act(async () => finishOld({ text: "Old reference content" }));
  expect(screen.queryByText("Old reference content")).toBeNull();
  expect(screen.getByText("Latest reference content")).toBeTruthy();
});

it("reloads versions after an acknowledged save without creating another draft or version", async () => {
  let detailAttempts = 0;
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "drafts.create") return { draft_id: "saved" };
    if (command === "drafts.detail") {
      if (++detailAttempts === 1) throw new Error("Temporarily unavailable");
      return {
        draft: { current_version_id: "v2" },
        versions: [
          {
            id: "v2",
            text: "A useful story",
            created_at: new Date().toISOString(),
          },
        ],
      };
    }
    return {};
  });
  const error = vi.fn();
  render(<DraftsPage snapshot={{ drafts: [] }} onError={error} />);
  fireEvent.click(screen.getAllByRole("button", { name: "New draft" })[0]);
  fireEvent.change(screen.getByRole("textbox", { name: "Title" }), {
    target: { value: "Story idea" },
  });
  fireEvent.change(screen.getByRole("textbox", { name: "Draft text" }), {
    target: { value: "A useful story" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await screen.findByText(
    "Your draft is saved. Saved versions could not load.",
  );
  expect(error).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Reload saved versions" }),
  );
  await waitFor(() =>
    expect(
      screen.queryByText("Your draft is saved. Saved versions could not load."),
    ).toBeNull(),
  );
  await screen.findByText("Draft saved.");
  expect(
    vi
      .mocked(call)
      .mock.calls.filter(([command]) => command === "drafts.create"),
  ).toHaveLength(1);
  expect(
    vi.mocked(call).mock.calls.filter(([command]) => command === "drafts.save"),
  ).toHaveLength(0);
});

it("keeps a new draft when an earlier draft finishes opening late", async () => {
  let resolveDetail: (result: unknown) => void = () => {};
  vi.mocked(call).mockImplementation(
    async () =>
      new Promise((resolve) => {
        resolveDetail = resolve;
      }),
  );
  render(
    <DraftsPage
      snapshot={{ drafts: [{ id: "old", topic: "Old story" }] }}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: /Old story/ }));
  expect(
    screen.getByRole("button", { name: /Old story/ }).getAttribute("aria-busy"),
  ).toBe("true");
  fireEvent.click(screen.getByRole("button", { name: "New draft" }));
  expect(screen.queryByText("Saved")).toBeNull();
  fireEvent.change(screen.getByRole("textbox", { name: "Draft text" }), {
    target: { value: "New writing" },
  });
  await act(async () =>
    resolveDetail({
      draft: { current_version_id: "v1" },
      versions: [{ id: "v1", text: "Old content" }],
    }),
  );
  expect(
    (screen.getByRole("textbox", { name: "Draft text" }) as HTMLTextAreaElement)
      .value,
  ).toBe("New writing");
});

it("does not mark a changed draft as copied when an older clipboard request finishes", async () => {
  let finish: () => void = () => {};
  const original = Object.getOwnPropertyDescriptor(navigator, "clipboard");
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: {
      writeText: () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    },
  });
  try {
    render(<DraftsPage snapshot={{ drafts: [] }} onError={vi.fn()} />);
    fireEvent.click(screen.getAllByRole("button", { name: "New draft" })[0]);
    const editor = screen.getByRole("textbox", { name: "Draft text" });
    fireEvent.change(editor, { target: { value: "First text" } });
    fireEvent.click(screen.getByRole("button", { name: "Copy text" }));
    fireEvent.change(editor, { target: { value: "Newer text" } });
    await act(async () => finish());
    expect(screen.queryByRole("button", { name: "Copied" })).toBeNull();
    expect(screen.getByRole("button", { name: "Copy text" })).toBeTruthy();
  } finally {
    if (original) Object.defineProperty(navigator, "clipboard", original);
    else Reflect.deleteProperty(navigator, "clipboard");
  }
});

it("checks every dirty editor before navigating rather than silently dropping a second editor", async () => {
  const leave = vi.fn();
  function Editor({ label }: { label: string }) {
    const guard = useUnsavedChanges(true, async () => true);
    return <section aria-label={label}>{guard.dialog}</section>;
  }
  render(
    <>
      <Editor label="First editor" />
      <Editor label="Second editor" />
    </>,
  );
  act(() => navigateSafely(leave));
  fireEvent.click(
    await screen.findByRole("button", { name: "Discard changes" }),
  );
  expect(leave).not.toHaveBeenCalled();
  fireEvent.click(
    await screen.findByRole("button", { name: "Discard changes" }),
  );
  expect(leave).toHaveBeenCalledOnce();
});
