// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { App } from "./main";
import { call } from "./engine";

vi.mock("react-dom/client", () => ({
  createRoot: () => ({ render: vi.fn() }),
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn(async () => false) }));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));
vi.mock("./pages", () => ({
  Articles: ({
    onDiscuss,
  }: {
    onDiscuss: (article: Record<string, unknown>) => void;
  }) => (
    <button
      onClick={() =>
        onDiscuss({ id: "story", title: "An interesting article" })
      }
    >
      Discuss article
    </button>
  ),
}));
vi.mock("./engine", async (original) => ({
  ...(await original<typeof import("./engine")>()),
  call: vi.fn(),
}));

beforeEach(() => {
  const values = new Map<string, string>();
  const storage = {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    clear: () => values.clear(),
  };
  vi.stubGlobal("localStorage", storage);
  vi.stubGlobal("sessionStorage", storage);
  localStorage.clear();
  localStorage.setItem("welcome-dismissed", "true");
  localStorage.setItem("model-consent", "true");
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.unstubAllGlobals();
});

function engine(send: (payload: Record<string, any>) => Promise<unknown>) {
  vi.mocked(call).mockImplementation(async (command, payload) => {
    if (command === "workspace.snapshot")
      return { profiles: [{ id: "p", label: "Local account", model_id: "m" }] };
    if (command === "chat.list") return { conversations: [] };
    if (command === "agents.list") return { agents: [] };
    if (command === "providers.models")
      return { models: [{ id: "m", name: "Local model" }] };
    if (command === "chat.create") return { conversation_id: "chat-created" };
    if (command === "chat.detail") return { id: "chat-created", messages: [] };
    if (command === "chat.send") return await send(payload!);
    return {};
  });
}
async function write(text: string) {
  await screen.findByRole("button", { name: "Choose model" });
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Choose model" }).textContent,
    ).toContain("Local model"),
  );
  fireEvent.change(screen.getByRole("textbox", { name: "Message" }), {
    target: { value: text },
  });
}

it("keeps follow-up writing when a slow send is acknowledged", async () => {
  let finish: (result: unknown) => void = () => {};
  engine(
    async () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  render(<App />);
  await write("First message");
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));
  await screen.findByRole("button", { name: "Sending message…" });
  fireEvent.change(screen.getByRole("textbox", { name: "Message" }), {
    target: { value: "A follow-up I am still writing" },
  });
  fireEvent.keyDown(screen.getByRole("textbox", { name: "Message" }), {
    key: "Enter",
  });
  await act(async () => finish({ job_id: "job-1" }));
  expect(
    (screen.getByRole("textbox", { name: "Message" }) as HTMLTextAreaElement)
      .value,
  ).toBe("A follow-up I am still writing");
  expect(
    vi.mocked(call).mock.calls.filter(([command]) => command === "chat.send"),
  ).toHaveLength(1);
  expect(
    JSON.parse(localStorage.getItem("composer-drafts")!)["chat-created"],
  ).toBe("A follow-up I am still writing");
});

it("keeps the new-chat draft on send failure and retries the same conversation and request", async () => {
  let attempts = 0;
  engine(async () => {
    if (++attempts === 1) throw new Error("Connection interrupted");
    return { job_id: "job-2" };
  });
  render(<App />);
  await write("Do not lose this message");
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));
  await screen.findByText("Error: Connection interrupted");
  expect(
    (screen.getByRole("textbox", { name: "Message" }) as HTMLTextAreaElement)
      .value,
  ).toBe("Do not lose this message");
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));
  await waitFor(() => expect(attempts).toBe(2));
  const calls = vi.mocked(call).mock.calls;
  expect(calls.filter(([command]) => command === "chat.create")).toHaveLength(
    1,
  );
  const requests = calls
    .filter(([command]) => command === "chat.send")
    .map(([, payload]) => payload);
  expect(requests[0]).toEqual(requests[1]);
  await waitFor(() =>
    expect(
      (screen.getByRole("textbox", { name: "Message" }) as HTMLTextAreaElement)
        .value,
    ).toBe(""),
  );
});

it("preserves existing writing when preparing a conversation about an article", async () => {
  engine(async () => ({ job_id: "unused" }));
  render(<App />);
  await write("An unfinished thought I want to keep");
  fireEvent.click(screen.getByRole("button", { name: "Articles" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Discuss article" }),
  );
  const editor = await screen.findByRole("textbox", { name: "Message" });
  expect((editor as HTMLTextAreaElement).value).toContain(
    "An unfinished thought I want to keep",
  );
  expect((editor as HTMLTextAreaElement).value).toContain(
    "An interesting article",
  );
  expect(
    screen.getByRole("button", { name: /An interesting article/ }),
  ).toBeTruthy();
  expect(
    vi.mocked(call).mock.calls.filter(([command]) => command === "chat.send"),
  ).toHaveLength(0);
});

it("requires explicit model consent without losing the message", async () => {
  localStorage.setItem("model-consent", "false");
  engine(async () => ({ job_id: "job-consent" }));
  render(<App />);
  await write("Send only after my consent");
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));
  await screen.findByText(
    "Enable model access below. Your message and selected context will be sent to your chosen provider.",
  );
  expect(
    vi.mocked(call).mock.calls.filter(([command]) => command === "chat.send"),
  ).toHaveLength(0);
  expect(
    (screen.getByRole("textbox", { name: "Message" }) as HTMLTextAreaElement)
      .value,
  ).toBe("Send only after my consent");
  fireEvent.click(
    screen.getByRole("checkbox", {
      name: "Allow sending messages and context to my selected model.",
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Send message" }));
  await waitFor(() =>
    expect(
      vi.mocked(call).mock.calls.filter(([command]) => command === "chat.send"),
    ).toHaveLength(1),
  );
});
