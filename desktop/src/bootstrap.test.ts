// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { invoke } from "@tauri-apps/api/core";
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockResolvedValue("Technical events only"),
}));
vi.mock("./main", () => {
  throw new Error("Module failed to load");
});
afterEach(() => {
  document.body.replaceChildren();
  vi.resetModules();
  vi.clearAllMocks();
});
it("leaves a working recovery and report action when the interface module cannot load", async () => {
  document.documentElement.lang = "en";
  const root = document.createElement("div");
  root.id = "root";
  document.body.append(root);
  await import("./bootstrap");
  await screen.findByRole("alert");
  expect(screen.getByRole("button", { name: "Reload interface" })).toBeTruthy();
  expect(document.querySelector("pre")?.textContent).toMatch(/^Error:/);
  expect(invoke).toHaveBeenCalledWith("record_diagnostic", {
    operation: "frontend.bootstrap",
    code: "UI_LOAD_FAILED",
  });
  fireEvent.click(screen.getByRole("button", { name: "Report this problem" }));
  await waitFor(() =>
    expect(invoke).toHaveBeenCalledWith("open_external", {
      address: expect.stringContaining("UI_LOAD_FAILED"),
    }),
  );
  const open = vi
    .mocked(invoke)
    .mock.calls.find(([command]) => command === "open_external");
  const payload = open?.[1] as { address?: string } | undefined;
  expect(String(payload?.address)).not.toContain("Module failed to load");
});
