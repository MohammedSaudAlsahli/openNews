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
import { call } from "./engine";
import { TaskInstructions } from "./task-instructions";
import { Connections } from "./connections";
import { invoke } from "@tauri-apps/api/core";
vi.mock("./engine", () => ({ call: vi.fn(), language: () => "en" }));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.restoreAllMocks();
  sessionStorage.clear();
});

it("keeps editors unavailable until saved settings load and allows a failed load to retry", async () => {
  const { default: Settings } = await import("./settings");
  sessionStorage.setItem("settings-tab", "instructions");
  let rejectLoad!: (error: Error) => void;
  vi.mocked(call).mockImplementation(
    () =>
      new Promise((_resolve, reject) => {
        rejectLoad = reject;
      }),
  );
  render(
    <Settings
      snapshot={{ sources: [] }}
      refresh={async () => {}}
      theme="light"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  expect(
    screen.queryByRole("textbox", { name: "Role & expertise" }),
  ).toBeNull();
  await act(async () => rejectLoad(new Error("Read failed")));
  expect(screen.getByRole("alert").textContent).toContain("Read failed");
  expect(
    screen.queryByRole("textbox", { name: "Role & expertise" }),
  ).toBeNull();
  vi.mocked(call).mockResolvedValue({ settings: { role: "Saved role" } });
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByDisplayValue("Saved role")).toBeTruthy();
});

it("does not replace a changed processing preference with an older status poll", async () => {
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value: "visible",
  });
  const { default: Settings } = await import("./settings");
  sessionStorage.setItem("settings-tab", "summaries");
  let poll!: () => Promise<void>,
    finishPoll!: (value: object) => void,
    finishWrite!: (value: object) => void;
  let statusCalls = 0;
  const originalInterval = globalThis.setInterval;
  vi.spyOn(globalThis, "setInterval").mockImplementation(((
    callback: () => Promise<void>,
    milliseconds: number,
  ) => {
    if (milliseconds !== 5000) return originalInterval(callback, milliseconds);
    poll = callback;
    return 1;
  }) as typeof setInterval);
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.digest.status") {
      if (++statusCalls === 1)
        return {
          enabled: false,
          phase: "disabled",
          engine: "provider",
          language: "ar",
        };
      return new Promise((resolve) => {
        finishPoll = resolve;
      });
    }
    if (command === "news.digest.set")
      return new Promise((resolve) => {
        finishWrite = resolve;
      });
    return { content: "# Instructions" };
  });
  render(
    <Settings
      snapshot={{
        sources: [],
        assignments: [
          { role: "news", profile_id: "p", model_id: "news-model" },
        ],
      }}
      refresh={async () => {}}
      theme="light"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  const toggle = (await screen.findByRole("checkbox", {
    name: "Automatic explanations",
  })) as HTMLInputElement;
  act(() => {
    void poll();
  });
  fireEvent.click(toggle);
  expect(toggle.disabled).toBe(true);
  expect(
    (screen.getByRole("combobox", { name: "Language" }) as HTMLSelectElement)
      .disabled,
  ).toBe(true);
  await act(async () =>
    finishWrite({
      enabled: true,
      phase: "ready",
      engine: "provider",
      language: "ar",
    }),
  );
  expect(toggle.checked).toBe(true);
  await act(async () => finishPoll({ enabled: false, phase: "disabled" }));
  expect(toggle.checked).toBe(true);
  expect(toggle.disabled).toBe(false);
});

it("guides missing explanation models to account setup without attempting to enable them", async () => {
  const { default: Settings } = await import("./settings");
  sessionStorage.setItem("settings-tab", "summaries");
  vi.mocked(call).mockImplementation(async (command) =>
    command === "providers.catalog"
      ? { providers: [] }
      : command === "instructions.get"
        ? { content: "# Instructions" }
        : { enabled: false, engine: "provider", phase: "disabled" },
  );
  render(
    <Settings
      snapshot={{ profiles: [], assignments: [] }}
      refresh={async () => {}}
      theme="light"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  const toggle = (await screen.findByRole("checkbox", {
    name: "Automatic explanations",
  })) as HTMLInputElement;
  expect(toggle.disabled).toBe(true);
  expect(
    screen.getByText("Choose a model before enabling explanations."),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Choose a model" }));
  await screen.findByRole("heading", { name: "Accounts & models" });
  expect(
    vi
      .mocked(call)
      .mock.calls.some(([command]) => command === "news.digest.set"),
  ).toBe(false);
});

it.each(["provider", "local"])(
  "shows the actual %s model assigned to explanations",
  async (engine) => {
    const { default: Settings } = await import("./settings");
    sessionStorage.setItem("settings-tab", "summaries");
    vi.mocked(call).mockImplementation(async (command) =>
      command === "instructions.get"
        ? { content: "# Instructions" }
        : {
            enabled: false,
            engine,
            local_model: "local:2b",
            phase: "disabled",
          },
    );
    render(
      <Settings
        snapshot={{
          assignments: [
            { role: "writer", model_id: "writing-model" },
            { role: "news", model_id: "cloud-news" },
          ],
        }}
        refresh={async () => {}}
        theme="light"
        setTheme={vi.fn()}
        onError={vi.fn()}
      />,
    );
    expect(
      (
        await screen.findAllByText(
          engine === "local" ? "local:2b" : "cloud-news",
        )
      )[0],
    ).toBeTruthy();
    expect(
      (
        screen.getByRole("checkbox", {
          name: "Automatic explanations",
        }) as HTMLInputElement
      ).disabled,
    ).toBe(false);
    expect(screen.queryByText("writing-model")).toBeNull();
  },
);

it("treats an acknowledged settings save as saved even when snapshot refresh fails", async () => {
  const { default: Settings } = await import("./settings");
  sessionStorage.setItem("settings-tab", "instructions");
  vi.mocked(call).mockResolvedValue({ settings: { role: "Original" } });
  render(
    <Settings
      snapshot={{ sources: [] }}
      refresh={async () => {
        throw new Error("Refresh offline");
      }}
      theme="light"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  fireEvent.change(await screen.findByDisplayValue("Original"), {
    target: { value: "Saved edit" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save instructions" }));
  await screen.findByRole("button", { name: "Saved" });
  expect(screen.getByDisplayValue("Saved edit")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "General" }));
  await screen.findByRole("heading", { name: "Appearance & language" });
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("loads the actual task instructions and saves edits to the same document", async () => {
  vi.mocked(call).mockResolvedValue({ content: "# Explain the whole article" });
  render(
    <TaskInstructions
      id="article-summary"
      title="Article instructions"
      onError={vi.fn()}
    />,
  );
  const editor = await screen.findByDisplayValue("# Explain the whole article");
  fireEvent.change(editor, { target: { value: "# Explain with context" } });
  fireEvent.click(screen.getByText("Save instructions"));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("instructions.save", {
      id: "article-summary",
      content: "# Explain with context",
    }),
  );
  expect(await screen.findByText("Saved")).toBeTruthy();
});
it("shows actual provider catalog failures instead of silently empty model choices", async () => {
  const error = vi.fn();
  vi.mocked(call).mockImplementation(async (command: string) =>
    command === "providers.catalog"
      ? { providers: [] }
      : { models: [], error: "Connection expired" },
  );
  render(
    <Connections
      snapshot={{
        profiles: [{ id: "test", provider_key: "openai", model_id: "" }],
      }}
      refresh={async () => {}}
      onError={error}
    />,
  );
  fireEvent.click(screen.getByText("Manage account"));
  fireEvent.click(screen.getByText("Refresh models"));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Connection expiredDismiss",
  );
  expect(error).not.toHaveBeenCalled();
});

it("keeps adding an account separate and advanced server settings collapsed", async () => {
  vi.mocked(call).mockResolvedValue({
    providers: [
      {
        id: "ollama",
        name: "Ollama",
        status: "ready",
        credential: "local_server",
        fields: ["host"],
      },
    ],
  });
  render(
    <Connections
      snapshot={{
        profiles: [{ id: "p", label: "My account", model_id: "model" }],
      }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  expect(screen.queryByLabelText("Provider")).toBeNull();
  fireEvent.click(screen.getByText("Add account"));
  await screen.findByText("Ollama");
  expect(
    screen.getByText("Advanced connection options").closest("details")?.open,
  ).toBe(false);
  fireEvent.click(screen.getByText("Cancel"));
  expect(screen.queryByLabelText("Provider")).toBeNull();
});

it("shows saved health and live check failures without leaving a green ready state", async () => {
  let rejectCheck: (reason: Error) => void = () => {};
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "providers.check")
      return new Promise((_resolve, reject) => {
        rejectCheck = reject;
      });
    return { providers: [] };
  });
  render(
    <Connections
      snapshot={{ profiles: [{ id: "p", connection: { state: "connected" } }] }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  expect(screen.getByText(/Ready/)).toBeTruthy();
  fireEvent.click(screen.getByText("Check connection"));
  expect(screen.queryByText(/^Ready$/)).toBeNull();
  expect(screen.getAllByText(/Checking connection/).length).toBeGreaterThan(0);
  rejectCheck(new Error("Network offline"));
  expect(await screen.findByText("Network offline")).toBeTruthy();
  expect(screen.getByText(/Could not verify/)).toBeTruthy();
});

it("does not call a saved but unchecked account ready", async () => {
  vi.mocked(call).mockResolvedValue({ providers: [] });
  render(
    <Connections
      snapshot={{
        profiles: [{ id: "p", connection: { state: "configured" } }],
      }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  expect(screen.getByText(/Not checked yet/)).toBeTruthy();
  expect(screen.getByText("Check connection")).toBeTruthy();
});

it("retries failed credential storage on the saved account without creating a duplicate", async () => {
  const providers = [
    { id: "ollama", status: "ready", credential: "local_server" },
    {
      id: "openai",
      name: "OpenAI",
      status: "ready",
      credential: "api_key",
      credential_fields: ["api_key"],
    },
  ];
  vi.mocked(call).mockImplementation(async (command) =>
    command === "providers.catalog"
      ? { providers }
      : command === "providers.save"
        ? { profile_id: "created-account" }
        : {},
  );
  vi.mocked(invoke)
    .mockRejectedValueOnce(new Error("Credential store unavailable"))
    .mockResolvedValue(undefined);
  render(
    <Connections
      snapshot={{ profiles: [] }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  await screen.findByRole("option", { name: "OpenAI" });
  fireEvent.change(screen.getByRole("combobox", { name: "Provider" }), {
    target: { value: "openai" },
  });
  fireEvent.change(screen.getByLabelText("API key"), {
    target: { value: "test-key-not-real" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Connect" }));
  await screen.findByText("Credential store unavailable");
  expect(
    (screen.getByRole("combobox", { name: "Provider" }) as HTMLSelectElement)
      .disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Save credentials" }));
  await screen.findByText("Credentials updated");
  expect(
    vi
      .mocked(call)
      .mock.calls.filter(([command]) => command === "providers.save"),
  ).toHaveLength(1);
  expect(
    vi
      .mocked(invoke)
      .mock.calls.filter(([command]) => command === "save_credentials"),
  ).toHaveLength(2);
  expect(invoke).toHaveBeenLastCalledWith("save_credentials", {
    profileId: "created-account",
    values: { api_key: "test-key-not-real" },
  });
});

it("validates service-account JSON before saving an account and does not echo credential text", async () => {
  vi.mocked(call).mockResolvedValue({
    providers: [
      { id: "ollama", status: "ready", credential: "local_server" },
      {
        id: "vertex",
        name: "Vertex",
        status: "ready",
        credential: "cloud_configuration",
        credential_fields: ["service_account_info"],
      },
    ],
  });
  render(
    <Connections
      snapshot={{ profiles: [] }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  await screen.findByRole("option", { name: "Vertex" });
  fireEvent.change(screen.getByRole("combobox", { name: "Provider" }), {
    target: { value: "vertex" },
  });
  fireEvent.change(
    screen.getByRole("textbox", { name: "Service account JSON" }),
    { target: { value: "private-value-invalid-json" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "Connect" }));
  expect(
    await screen.findByText(
      "Service account JSON is invalid. Paste a valid JSON object.",
    ),
  ).toBeTruthy();
  expect(
    vi
      .mocked(call)
      .mock.calls.filter(([command]) => command === "providers.save"),
  ).toHaveLength(0);
  expect(screen.getByRole("alert").textContent).not.toContain("private-value");
});

it("keeps a verified connection ready when only refreshing the workspace fails", async () => {
  vi.mocked(call).mockImplementation(async (command) =>
    command === "providers.check"
      ? { state: "connected", checked_at: new Date().toISOString() }
      : { providers: [] },
  );
  render(
    <Connections
      snapshot={{
        profiles: [{ id: "p", connection: { state: "configured" } }],
      }}
      refresh={async () => {
        throw new Error("Snapshot unavailable");
      }}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Check connection" }));
  await screen.findByText(
    "Connection checked. The account list will update when you refresh.",
  );
  expect(screen.getByText("Ready")).toBeTruthy();
  expect(screen.queryByText("Could not verify")).toBeNull();
});

it("retries a failed provider catalog and protects typed credentials before navigation", async () => {
  let attempts = 0;
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "providers.catalog") {
      if (++attempts === 1) throw new Error("Unavailable");
      return {
        providers: [
          {
            id: "ollama",
            name: "Ollama",
            status: "ready",
            credential: "local_server",
          },
        ],
      };
    }
    return {};
  });
  render(
    <Connections
      snapshot={{ profiles: [] }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  await screen.findByText("Providers could not load.");
  expect(
    (screen.getByRole("button", { name: "Connect" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("option", { name: "Ollama" });
  fireEvent.change(
    screen.getByRole("textbox", { name: "Connection name (optional)" }),
    { target: { value: "My private connection" } },
  );
  const { navigateSafely } = await import("./unsaved-changes");
  const leave = vi.fn();
  act(() => navigateSafely(leave));
  expect(leave).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Keep editing" }));
  expect(
    (
      screen.getByRole("textbox", {
        name: "Connection name (optional)",
      }) as HTMLInputElement
    ).value,
  ).toBe("My private connection");
});

it("groups customization without losing instruction edits when opening references", async () => {
  const { default: Settings } = await import("./settings");
  sessionStorage.setItem("settings-tab", "instructions");
  vi.mocked(call).mockResolvedValue({
    settings: { role: "Original instructions" },
  });
  render(
    <Settings
      snapshot={{ sources: [] }}
      refresh={async () => {}}
      theme="dark"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  const editor = await screen.findByDisplayValue("Original instructions");
  fireEvent.change(editor, { target: { value: "My edited instructions" } });
  fireEvent.click(
    screen.getByRole("button", { name: "Examples & references" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Instructions & style" }));
  expect(screen.getByDisplayValue("My edited instructions")).toBeTruthy();
  expect(screen.queryByRole("button", { name: /^Assistants$/ })).toBeNull();
  expect(
    screen.getByText("Advanced: specialized assistants").closest("details")
      ?.open,
  ).toBe(false);
  fireEvent.click(screen.getByText("Save instructions"));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("assistant.save", {
      scope: "general",
      target_id: "",
      settings: { role: "My edited instructions" },
    }),
  );
  sessionStorage.clear();
});

it("finds an individual preference and opens its grouped destination", async () => {
  const { default: Settings } = await import("./settings");
  vi.mocked(call).mockResolvedValue({ runtime: true, phase: "ready" });
  render(
    <Settings
      snapshot={{}}
      refresh={async () => {}}
      theme="light"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  const search = screen.getByRole("textbox", { name: "Find a setting" });
  fireEvent.change(search, { target: { value: "battery" } });
  fireEvent.click(screen.getByRole("button", { name: "Local models" }));
  await screen.findByRole("heading", { name: "Local models" });
  expect(
    screen
      .getByRole("button", { name: "AI models" })
      .getAttribute("aria-current"),
  ).toBe("page");
  expect(
    screen.getByRole("button", { name: "Accounts & models" }),
  ).toBeTruthy();
  expect((search as HTMLInputElement).value).toBe("");
});

it("keeps an unsaved writing guide mounted while searching and guards result navigation", async () => {
  const { default: Settings } = await import("./settings");
  sessionStorage.setItem("settings-tab", "skills");
  vi.mocked(call).mockImplementation(async (command) =>
    command === "skills.catalog"
      ? {
          skills: [
            {
              id: "research",
              title_en: "Research",
              description_en: "Find sources",
              origin: "builtin",
            },
          ],
        }
      : { content: "Saved guide" },
  );
  render(
    <Settings
      snapshot={{}}
      refresh={async () => {}}
      theme="light"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(await screen.findByRole("button", { name: /Research/ }));
  fireEvent.change(await screen.findByDisplayValue("Saved guide"), {
    target: { value: "Unsaved guide" },
  });
  fireEvent.change(screen.getByRole("textbox", { name: "Find a setting" }), {
    target: { value: "schedule" },
  });
  fireEvent.click(
    screen.getAllByRole("button", { name: "Daily report" }).at(-1)!,
  );
  await screen.findByRole("dialog");
  fireEvent.click(screen.getByRole("button", { name: "Keep editing" }));
  fireEvent.click(screen.getByRole("button", { name: "Clear search" }));
  expect(screen.getByDisplayValue("Unsaved guide")).toBeTruthy();
  expect(
    vi
      .mocked(call)
      .mock.calls.some(([command]) => command === "instructions.save"),
  ).toBe(false);
});

it("finds translated preference labels in Arabic", async () => {
  const { setLocale } = await import("./locale");
  const { default: Settings } = await import("./settings");
  act(() => setLocale("ar"));
  try {
    render(
      <Settings
        snapshot={{}}
        refresh={async () => {}}
        theme="dark"
        setTheme={vi.fn()}
        onError={vi.fn()}
      />,
    );
    fireEvent.change(
      screen.getByRole("textbox", { name: "ابحث في الإعدادات" }),
      { target: { value: "البطارية" } },
    );
    expect(
      screen.getByRole("button", {
        name: "النماذج المحلية",
      }),
    ).toBeTruthy();
  } finally {
    act(() => setLocale("en"));
  }
});

it("changes a search model in place without leaving article settings or clearing the model search", async () => {
  const { default: Settings } = await import("./settings");
  sessionStorage.setItem("settings-tab", "search");
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.search.status")
      return { enabled: true, model: "search:small", phase: "ready" };
    if (command === "news.local.available")
      return {
        installed: [
          { id: "search:small", capabilities: ["embedding"], size: 1e8 },
          { id: "writer:small", capabilities: ["completion"], size: 1e9 },
        ],
      };
    if (command === "news.local.inspect")
      return { can_download: true, fit: "fits", capabilities: ["embedding"] };
    return { download: { phase: "idle" } };
  });
  render(
    <Settings
      snapshot={{}}
      refresh={async () => {}}
      theme="dark"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(await screen.findByRole("button", { name: /Change model/ }));
  await screen.findByRole("button", { name: /writer:small/ });
  fireEvent.change(screen.getByRole("searchbox", { name: "Search models" }), {
    target: { value: "search" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: /search:small/, pressed: false }),
  );
  await screen.findByRole("button", { name: "Use this model" });
  expect(sessionStorage.getItem("settings-tab")).toBe("search");
  expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe(
    "search",
  );
  expect(
    screen
      .getByRole("button", { name: "Article search" })
      .getAttribute("aria-current"),
  ).toBe("page");
  expect(
    vi
      .mocked(call)
      .mock.calls.some(([command]) => command === "news.local.download"),
  ).toBe(false);
});

it("reopens the last settings page after returning from another part of the app", async () => {
  const { default: Settings } = await import("./settings");
  vi.mocked(call).mockResolvedValue({ enabled: false, phase: "disabled" });
  const props = {
    snapshot: {},
    refresh: async () => {},
    theme: "dark",
    setTheme: vi.fn(),
    onError: vi.fn(),
  };
  const mounted = render(<Settings {...props} />);
  fireEvent.click(screen.getByRole("button", { name: "Your articles" }));
  fireEvent.click(screen.getByRole("button", { name: "Article search" }));
  expect(sessionStorage.getItem("settings-tab")).toBe("search");
  mounted.unmount();
  render(<Settings {...props} />);
  expect(
    screen
      .getByRole("button", { name: "Article search" })
      .getAttribute("aria-current"),
  ).toBe("page");
});
