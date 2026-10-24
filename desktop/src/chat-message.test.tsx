// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { ChatMessage } from "./chat-message";
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
const message = {
  id: "m1",
  role: "assistant",
  content: "The answer",
  outputs: [{ text: "Draft text", title: "Saved draft" }],
};
it("confirms the copied draft separately from the response and clears feedback", async () => {
  vi.useFakeTimers();
  const writeText = vi.fn().mockResolvedValue(undefined);
  vi.stubGlobal("navigator", { clipboard: { writeText } });
  render(<ChatMessage message={message} onError={vi.fn()} onDraft={vi.fn()} />);
  await act(async () =>
    fireEvent.click(screen.getByRole("button", { name: "Copy draft" })),
  );
  expect(writeText).toHaveBeenCalledWith("Draft text");
  expect(screen.getByRole("button", { name: "Copy response" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Copied" })).toBeTruthy();
  await act(async () => vi.advanceTimersByTime(1800));
  expect(screen.getByRole("button", { name: "Copy draft" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Copied" })).toBeNull();
});
it("does not mark a different message as copied when an earlier clipboard operation finishes", async () => {
  let finish!: () => void;
  vi.stubGlobal("navigator", {
    clipboard: {
      writeText: () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    },
  });
  const { rerender } = render(
    <ChatMessage message={message} onError={vi.fn()} onDraft={vi.fn()} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Copy response" }));
  rerender(
    <ChatMessage
      message={{ ...message, id: "m2", content: "A new answer" }}
      onError={vi.fn()}
      onDraft={vi.fn()}
    />,
  );
  await act(async () => finish());
  expect(screen.queryByRole("button", { name: "Copied" })).toBeNull();
  expect(screen.getByRole("button", { name: "Copy response" })).toBeTruthy();
});
it("keeps the copy action available when clipboard permission fails", async () => {
  const error = vi.fn();
  vi.stubGlobal("navigator", {
    clipboard: {
      writeText: vi.fn().mockRejectedValue(Error("Clipboard unavailable")),
    },
  });
  render(<ChatMessage message={message} onError={error} onDraft={vi.fn()} />);
  await act(async () =>
    fireEvent.click(screen.getByRole("button", { name: "Copy response" })),
  );
  expect(error).toHaveBeenCalledWith("Error: Clipboard unavailable");
  expect(screen.getByRole("button", { name: "Copy response" })).toBeTruthy();
});
