// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { NavigationRail } from "./navigation-rail";
afterEach(cleanup);

it("keeps named destinations and selected location available while the sidebar is collapsed", () => {
  const onNavigate = vi.fn(),
    onNew = vi.fn(),
    onExpand = vi.fn(),
    onHelp = vi.fn();
  const props = {
    page: "articles",
    busy: 2,
    onNavigate,
    onNew,
    onExpand,
    onHelp,
  };
  const { rerender } = render(<NavigationRail {...props} />);
  expect(
    screen.getByRole("navigation", { name: "Main navigation" }),
  ).toBeTruthy();
  expect(
    screen
      .getByRole("button", { name: "Articles" })
      .getAttribute("aria-current"),
  ).toBe("page");
  fireEvent.click(screen.getByRole("button", { name: "Saved drafts" }));
  expect(onNavigate).toHaveBeenLastCalledWith("drafts");
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  expect(onNavigate).toHaveBeenLastCalledWith("settings");
  fireEvent.click(screen.getByRole("button", { name: "Conversations" }));
  fireEvent.click(screen.getByRole("button", { name: "Show sidebar" }));
  expect(onExpand).toHaveBeenCalledTimes(2);
  fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
  expect(onNew).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole("button", { name: "Help & diagnostics" }));
  expect(onHelp).toHaveBeenCalledOnce();
  rerender(<NavigationRail {...props} page="settings" />);
  expect(
    screen
      .getByRole("button", { name: "Articles" })
      .hasAttribute("aria-current"),
  ).toBe(false);
  expect(
    screen
      .getByRole("button", { name: "Settings" })
      .getAttribute("aria-current"),
  ).toBe("page");
});
