// @vitest-environment jsdom
import React from "react";
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
const invoke = vi.hoisted(() => vi.fn());
vi.mock("./app-channel", () => ({ DEVELOPMENT: true }));
vi.mock("@tauri-apps/api/core", () => ({ invoke }));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(() => {}),
}));
import { Updates } from "./updates";
it("does not offer the official updater inside the development workspace", () => {
  render(<Updates onError={vi.fn()} />);
  expect(screen.getByRole("heading", { name: "openNews Dev" })).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
  expect(invoke).not.toHaveBeenCalled();
});
