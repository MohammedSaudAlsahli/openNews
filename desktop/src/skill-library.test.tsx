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
  within,
} from "@testing-library/react";
import { SkillLibrary } from "./skill-library";
import { call } from "./engine";
vi.mock("./engine", () => ({ call: vi.fn() }));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
const builtin = {
  id: "research",
  title_en: "Research",
  description_en: "Find sources and compare claims",
  origin: "builtin",
};
const preview = {
  kind: "skill",
  id: "article-guide",
  title: "Article guide",
  description: "Write useful articles",
  content: "Preserve facts",
  repository: "a/b",
  source_url: "https://github.com/a/b/blob/commit/SKILL.md",
  supporting_files: true,
};
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
function mock() {
  vi.mocked(call).mockImplementation(async (command) =>
    command === "skills.catalog"
      ? { skills: [builtin] }
      : command === "skills.preview"
        ? preview
        : command === "instructions.get"
          ? { content: "Original instructions", limit: 12000 }
          : { skills: [] },
  );
}
async function openPreview() {
  fireEvent.click(screen.getByRole("button", { name: "Add from a link" }));
  fireEvent.change(
    screen.getByRole("textbox", { name: "Skill or repository link" }),
    { target: { value: "https://github.com/a/b" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "Preview skill" }));
  await screen.findByRole("heading", { name: "Review before adding" });
}
it("starts with useful named skills and opens their actual instructions", async () => {
  mock();
  const use = vi.fn();
  render(<SkillLibrary onUse={use} />);
  fireEvent.click(await screen.findByRole("button", { name: /Research/ }));
  await screen.findByDisplayValue("Original instructions");
  fireEvent.click(
    screen.getByRole("button", { name: "Try in a conversation" }),
  );
  expect(use).toHaveBeenCalledWith("research");
  expect(screen.queryByRole("button", { name: "Remove skill" })).toBeNull();
});
it("previews source capabilities before adding and retains edits after a failed addition", async () => {
  mock();
  render(<SkillLibrary />);
  await openPreview();
  expect(
    screen.getByText(/Scripts and extra tools are not installed/),
  ).toBeTruthy();
  expect(
    screen.getByText(/steps that depend on those extras may not work/),
  ).toBeTruthy();
  fireEvent.change(screen.getByRole("textbox", { name: "Skill name" }), {
    target: { value: "My article guide" },
  });
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "skills.add") throw new Error("Command already exists");
    return {};
  });
  fireEvent.click(screen.getByRole("button", { name: "Add to your skills" }));
  await screen.findByRole("alert");
  expect(screen.getByDisplayValue("My article guide")).toBeTruthy();
  vi.mocked(call).mockResolvedValue({ content: "Preserve facts" });
  fireEvent.click(screen.getByRole("button", { name: "Add to your skills" }));
  await screen.findByText(
    "Skill added. It is ready for your next conversation.",
  );
  expect(call).toHaveBeenCalledWith(
    "skills.add",
    expect.objectContaining({
      id: "article-guide",
      title: "My article guide",
      content: "Preserve facts",
      source_url: preview.source_url,
    }),
  );
});
it("searches the online directory by topic and previews the chosen result", async () => {
  mock();
  vi.mocked(call).mockImplementation(async (command) =>
    command === "skills.catalog"
      ? { skills: [] }
      : command === "skills.search"
        ? {
            skills: [
              {
                id: "a/b/article-guide",
                title: "article-guide",
                repository: "a/b",
                source_url: "https://skills.sh/a/b/article-guide",
              },
            ],
          }
        : preview,
  );
  render(<SkillLibrary />);
  fireEvent.click(
    screen.getAllByRole("button", { name: "Discover skills" })[0],
  );
  await screen.findByText("article-guide");
  fireEvent.click(screen.getByRole("button", { name: "Newsletters" }));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("skills.search", {
      query: "newsletter writing",
    }),
  );
  const origin = await screen.findByRole("button", { name: "Preview skill" });
  origin.focus();
  fireEvent.click(origin);
  await screen.findByRole("heading", { name: "Review before adding" });
  await waitFor(() =>
    expect(document.activeElement).toBe(
      screen.getByRole("heading", { name: "Review before adding" }),
    ),
  );
  expect(call).toHaveBeenCalledWith("skills.preview", {
    url: "https://skills.sh/a/b/article-guide",
  });
  fireEvent.click(screen.getByRole("button", { name: "Back to discovery" }));
  await waitFor(() =>
    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Preview skill" }),
    ),
  );
});
it("keeps a reviewed import when the user cancels leaving it", async () => {
  mock();
  render(<SkillLibrary />);
  await openPreview();
  fireEvent.change(screen.getByRole("textbox", { name: "Skill name" }), {
    target: { value: "My edited skill" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Back to your skills" }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "Keep editing" }));
  expect(screen.getByDisplayValue("My edited skill")).toBeTruthy();
  expect(
    vi.mocked(call).mock.calls.some(([command]) => command === "skills.add"),
  ).toBe(false);
});

it("lets the user leave an unchanged preview without an extra confirmation", async () => {
  mock();
  render(<SkillLibrary />);
  await openPreview();
  fireEvent.click(screen.getByRole("button", { name: "Back to your skills" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(
    vi.mocked(call).mock.calls.some(([command]) => command === "skills.add"),
  ).toBe(false);
});

it("suggests a free command when an imported name matches an existing skill", async () => {
  mock();
  vi.mocked(call).mockImplementation(async (command) =>
    command === "skills.catalog"
      ? { skills: [builtin] }
      : { ...preview, id: "research" },
  );
  render(<SkillLibrary />);
  await screen.findByRole("button", { name: "Research" });
  await openPreview();
  expect(
    screen.getByRole("textbox", { name: "Command" }).getAttribute("value"),
  ).toBe("research-2");
});

it("lets the user ask the assistant for recommendations without sending a message automatically", async () => {
  mock();
  const recommend = vi.fn();
  render(<SkillLibrary onRecommend={recommend} />);
  fireEvent.click(
    screen.getAllByRole("button", { name: "Discover skills" })[0],
  );
  fireEvent.click(
    await screen.findByRole("button", {
      name: "Ask the assistant to suggest useful skills",
    }),
  );
  expect(recommend).toHaveBeenCalledOnce();
  expect(
    vi
      .mocked(call)
      .mock.calls.some(
        ([command]) => command === "chat.send" || command === "skills.add",
      ),
  ).toBe(false);
});

it("hands keyboard focus to details and restores the originating library row", async () => {
  mock();
  render(<SkillLibrary />);
  const row = await screen.findByRole("button", { name: "Research" });
  row.focus();
  fireEvent.click(row);
  expect(document.activeElement).toBe(
    screen.getByRole("heading", { name: "Research" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Back to your skills" }));
  expect(document.activeElement).toBe(
    screen.getByRole("button", { name: "Research" }),
  );
});

it("focuses link entry, review and added details without stealing focus while editing", async () => {
  mock();
  render(<SkillLibrary />);
  fireEvent.click(screen.getByRole("button", { name: "Add from a link" }));
  const url = screen.getByRole("textbox", { name: "Skill or repository link" });
  expect(document.activeElement).toBe(url);
  fireEvent.change(url, { target: { value: "https://github.com/a/b" } });
  fireEvent.click(screen.getByRole("button", { name: "Preview skill" }));
  const reviewHeading = await screen.findByRole("heading", {
    name: "Review before adding",
  });
  await waitFor(() => expect(document.activeElement).toBe(reviewHeading));
  const name = screen.getByRole("textbox", { name: "Skill name" });
  name.focus();
  fireEvent.change(name, { target: { value: "My guide" } });
  expect(document.activeElement).toBe(name);
  fireEvent.click(screen.getByRole("button", { name: "Add to your skills" }));
  const detail = await screen.findByRole("heading", { name: "My guide" });
  expect(document.activeElement).toBe(detail);
  fireEvent.click(screen.getByRole("button", { name: "Back to your skills" }));
  expect(document.activeElement).toBe(
    screen.getByRole("button", { name: "My guide" }),
  );
});
