/* Opt-in, debug-only native WebKit smoke test. Uses the real React controls,
   Rust bridge and packaged engine, only in com.opennews.ui-qa. */
void (async () => {
  if (window.__openNewsNativeQA) return;
  window.__openNewsNativeQA = true;
  const invoke = window.__TAURI_INTERNALS__.invoke;
  // This opt-in runner simulates foreground interactions even when Codex covers
  // its window. WebKit suppresses animation frames in an occluded view, including
  // the geometry pass that creates the real native article browser.
  const frame = window.requestAnimationFrame.bind(window);
  const cancelFrame = window.cancelAnimationFrame.bind(window);
  const hiddenFrames = new Set();
  window.requestAnimationFrame = (callback) => {
    if (document.visibilityState !== "hidden") return frame(callback);
    const id = setTimeout(() => { hiddenFrames.delete(id); callback(performance.now()); }, 16);
    hiddenFrames.add(id);
    return id;
  };
  window.cancelAnimationFrame = (id) => {
    if (hiddenFrames.delete(id)) clearTimeout(id); else cancelFrame(id);
  };
  window.addEventListener("error", (event) => {
    void invoke("record_diagnostic", { operation: "ui.qa", code: ("JS_" + event.message).replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 60) });
  });
  window.addEventListener("unhandledrejection", (event) => {
    void invoke("record_diagnostic", { operation: "ui.qa", code: ("PROMISE_" + String(event.reason)).replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 60) });
  });
  if (localStorage.getItem("interface-language") === "ar") {
    localStorage.setItem("interface-language", "en");
    location.reload();
    return;
  }
  const pause = () => new Promise((resolve) => setTimeout(resolve, 100));
  async function until(read) {
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
      const value = await read();
      if (value) return value;
      await pause();
    }
    throw new Error("Condition timed out");
  }
  const assert = (value) => {
    if (!value) throw new Error("Assertion failed");
  };
  const call = (command, payload = {}) =>
    invoke("engine_call", { command, payload });
  const name = (node) =>
    node.getAttribute("aria-label") || node.textContent.trim() || node.title;
  const button = (label) =>
    [...document.querySelectorAll("button")].find(
      (node) => name(node) === label,
    );
  const click = async (label) => {
    const settingsParents = {
      "Appearance & language": "General", "Privacy & updates": "General",
      "Local models": "AI models", "Accounts & models": "AI models",
      "Customize assistant": "Assistant & writing", "Writing skills": "Assistant & writing",
      "Article search": "Your articles", "Article explanations": "Your articles",
    };
    if (document.querySelector(".settings-layout") && settingsParents[label] && !button(label)) {
      const parent = await until(() => button(settingsParents[label]));
      parent.click();
    }
    const node = await until(() => button(label));
    assert(!node.disabled);
    node.click();
  };
  const enter = (field, value) => {
    const prototype =
      field.tagName === "TEXTAREA"
        ? HTMLTextAreaElement.prototype
        : field.tagName === "SELECT"
          ? HTMLSelectElement.prototype
          : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, "value").set.call(field, value);
    field.dispatchEvent(new Event("input", { bubbles: true }));
    if (field.tagName === "SELECT")
      field.dispatchEvent(new Event("change", { bubbles: true }));
  };
  const checkpoint = (code) =>
    invoke("record_diagnostic", { operation: "ui.qa", code });
  let stage = "START";
  try {
    await until(() => document.querySelector(".app"));
    await until(async () => {
      try {
        return await call("runtime.health");
      } catch {
        return false;
      }
    });
    await until(() => button("Settings"));
    await checkpoint("STARTED");

    stage = "KEYBOARD_SETTINGS";
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: ",", metaKey: true, bubbles: true }),
    );
    await until(() => document.querySelector(".settings-layout"));
    await checkpoint(stage);

    stage = "LOCAL_PROCESSING_POLICY";
    await click("Local models");
    const preferences = await until(() =>
      document.querySelector(".processing-pause button:not(:disabled)"),
    );
    const originalPolicy = await call("news.local.policy");
    try {
      const mode = document.querySelector(".local-models-settings select");
      const changedMode =
        originalPolicy.mode === "quiet" ? "balanced" : "quiet";
      enter(mode, changedMode);
      await until(
        async () => (await call("news.local.policy")).mode === changedMode,
      );
      await until(() => !preferences.disabled);
      preferences.click();
      await until(
        async () =>
          (await call("news.local.policy")).paused === !originalPolicy.paused,
      );
      await checkpoint(stage);
    } finally {
      await call("news.local.policy.set", {
        mode: originalPolicy.mode,
        paused: originalPolicy.paused,
        index_on_battery: originalPolicy.index_on_battery,
      });
    }
    stage = "INSTRUCTIONS";
    await click("Customize assistant");
    const editor = await until(() =>
      document.querySelector('textarea[aria-label="Role & expertise"]'),
    );
    const original = editor.value;
    assert(original.length > 10);
    enter(editor, original + "\nNative QA example.");
    await click("Save instructions");
    await until(() => button("Saved"));
    assert(
      (
        await call("assistant.get", { scope: "general" })
      ).settings.role.endsWith("Native QA example."),
    );
    enter(editor, original);
    await click("Save instructions");
    await until(() => button("Saved"));
    assert(
      (await call("assistant.get", { scope: "general" })).settings.role ===
        original,
    );
    await checkpoint(stage);

    stage = "WRITING_SKILL_LIBRARY";
    const skillId = "native-qa-" + Date.now();
    const skillText = "Write a clear, source-grounded editorial paragraph.";
    await call("skills.add", { id: skillId, title: "Native QA writing guide", description: "Test an imported writing guide", content: skillText });
    try {
      await click("Writing skills");
      const row = await until(() => document.querySelector(`[data-skill-id="${skillId}"]`));
      row.click();
      const skillEditor = await until(() => document.querySelector('textarea[aria-label="Skill instructions"]'));
      await until(() => skillEditor.value === skillText);
      enter(skillEditor, skillText + " Preserve all names.");
      await click("Save instructions");
      await until(() => button("Saved"));
      await until(async () => (await call("instructions.get", { id: "skill:" + skillId })).content.endsWith("Preserve all names."));
      await click("Try in a conversation");
      const composer = await until(() => document.querySelector('.composer textarea'));
      assert(composer.value.startsWith("/" + skillId + " "));
      enter(composer, composer.value.slice(skillId.length + 2));
      await click("Settings");
    } finally {
      await call("skills.remove", { id: skillId });
    }
    await checkpoint(stage);
    stage = "SKILL_RECOMMENDATION_STARTER";
    await click("Writing skills");
    await click("Discover skills");
    await click("Ask the assistant to suggest useful skills");
    const suggestedMessage = await until(() => document.querySelector(".composer textarea"));
    assert(suggestedMessage.value.includes("Find useful writing and research skills for openNews."));
    enter(suggestedMessage, suggestedMessage.value.split("Find useful writing and research skills for openNews.")[0].trimEnd());
    await checkpoint(stage);

    stage = "SOURCE_DISCOVERY";
    await click("Sources");
    const subscribed = (await call("workspace.snapshot")).subscriptions || [];
    if (subscribed.length) {
      stage = "SOURCE_INTERVAL";
      const source = subscribed[0];
      const trigger = await until(() =>
        [...document.querySelectorAll("button[aria-label]")].find(
          (node) =>
            node.getAttribute("aria-label") ===
            "Manage source: " + source.title,
        ),
      );
      trigger.focus();
      trigger.dispatchEvent(
        new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
      );
      const intervalItem = await until(() =>
        [...document.querySelectorAll('[role="menuitem"]')].find(
          (node) => node.textContent.trim() === "Refresh interval",
        ),
      );
      intervalItem.click();
      const interval = await until(() =>
        document.querySelector(
          'select[aria-label="Refresh interval ' +
            CSS.escape(source.title) +
            '"]',
        ),
      );
      const originalInterval = source.interval_minutes ?? 5;
      const changedInterval = originalInterval === 60 ? 5 : 60;
      try {
        enter(interval, String(changedInterval));
        await until(
          () =>
            document.querySelector(".interval-feedback")?.textContent ===
            "Saved",
        );
        assert(
          (await call("workspace.snapshot")).subscriptions.find(
            (row) => row.id === source.id,
          ).interval_minutes === changedInterval,
        );
      } finally {
        await call("news.update", {
          subscription_id: source.id,
          interval_minutes: originalInterval,
        });
      }
      await click("Close interval settings");
      await until(() => !document.querySelector(".refresh-interval"));
      assert(
        document.activeElement?.getAttribute("aria-label") ===
          "Manage source: " + source.title,
      );
      await checkpoint(stage);
    }
    stage = "SOURCE_DISCOVERY";
    await click("Discover");
    await until(() => document.querySelectorAll(".source-card").length > 0);
    assert(document.querySelector("select") !== null);
    await checkpoint(stage);

    stage = "DRAFT_SAVE";
    await click("Saved drafts");
    await click("New draft");
    const title = await until(() =>
      document.querySelector('input[aria-label="Title"]'),
    );
    let draft = document.querySelector('textarea[aria-label="Draft text"]');
    enter(title, "Native QA · editor flow");
    enter(draft, "# Native editor\n\nSaved through the real interface.");
    await click("Save draft");
    await until(
      () =>
        document.querySelector(".draft-save-state")?.textContent === "Saved",
    );
    assert(
      (await call("workspace.snapshot")).drafts.some(
        (row) => row.topic === "Native QA · editor flow",
      ),
    );
    await checkpoint(stage);

    stage = "DRAFT_PREVIEW_EXPORT";
    await click("Preview");
    await until(() =>
      document
        .querySelector(".draft-preview")
        ?.textContent.includes("Saved through the real interface."),
    );
    await click("Export Markdown");
    const exported = await until(
      () =>
        [...document.querySelectorAll(".inline-success")].find((node) =>
          node.textContent.includes("Exported to"),
        )?.textContent,
    );
    const exportName = exported.match(/openNews-([a-f0-9-]+)\.md/)?.[1];
    assert(exportName);
    await checkpoint("DRAFT_EXPORTED_" + exportName);
    await click("Write");
    draft = await until(() =>
      document.querySelector('textarea[aria-label="Draft text"]'),
    );
    await checkpoint(stage);

    stage = "PROTECTED_NAVIGATION";
    enter(draft, draft.value + "\nUnsaved addition.");
    await click("Articles");
    await click("Keep editing");
    assert(
      document
        .querySelector('textarea[aria-label="Draft text"]')
        .value.endsWith("Unsaved addition."),
    );
    await click("Articles");
    await click("Discard changes");
    await until(() => document.querySelector(".article-filters"));
    assert(!document.querySelector('[role="dialog"]'));
    await checkpoint(stage);

    stage = "CONVERSATION_CONTEXT";
    const contextTitle = "Native QA · conversation context · " + Date.now();
    const contextChat = await call("chat.create", { title: contextTitle });
    // Wait for normal workspace polling; the runner must not reach into React.
    await click(contextTitle);
    await click("Add to conversation");
    const chooseArticles = await until(() =>
      [...document.querySelectorAll(".attachment-menu button")].find((node) =>
        node.textContent.includes("Choose saved articles"),
      ),
    );
    chooseArticles.click();
    await click("Conversation instructions");
    const contextEditor = await until(() => {
      const node = document.querySelector(
        'textarea[aria-label="Conversation instructions"]',
      );
      return node && !node.disabled ? node : false;
    });
    const originalContext = (
      await call("assistant.get", {
        scope: "conversation",
        target_id: contextChat.conversation_id,
      })
    ).settings;
    try {
      enter(contextEditor, "Native QA · keep instructions until saved.");
      await click("Close");
      await click("Keep editing");
      assert(contextEditor.value.includes("until saved"));
      await click("Save instructions");
      await until(() => button("Saved"));
      assert(
        (
          await call("assistant.get", {
            scope: "conversation",
            target_id: contextChat.conversation_id,
          })
        ).settings.instructions.includes("until saved"),
      );
      await click("Close");
    } finally {
      await call("assistant.save", {
        scope: "conversation",
        target_id: contextChat.conversation_id,
        settings: originalContext,
      });
    }
    await checkpoint(stage);
    await click("Articles");
    await until(() => document.querySelector(".article-filters"));

    stage = "SUMMARY_SETUP";
    await click("Explanation settings");
    await until(() => document.querySelector(".summary-model-choice"));
    assert(
      document.querySelector('.settings-content input[type="checkbox"]')
        .disabled,
    );
    await click("Choose a model");
    await until(() =>
      [...document.querySelectorAll("h2")].some(
        (node) => node.textContent === "Accounts & models",
      ),
    );
    await checkpoint(stage);
    await click("Articles");
    await until(() => document.querySelector(".article-filters"));

    stage = "DAILY_SCHEDULE";
    const schedule = (await call("daily.get")).settings;
    assert(!schedule.enabled);
    await click("Settings");
    await click("Daily report");
    const clock = await until(() =>
      document.querySelector('input[type="time"]'),
    );
    enter(clock, "09:15");
    enter(document.querySelector('select[aria-label="Time zone"]'), "UTC");
    await click("Save schedule");
    await until(() => button("Saved"));
    const savedSchedule = (await call("daily.get")).settings;
    assert(
      savedSchedule.hour === 9 &&
        savedSchedule.minute === 15 &&
        savedSchedule.timezone === "UTC" &&
        !savedSchedule.enabled,
    );
    await call("daily.set", { ...schedule, consent: true });
    await checkpoint(stage);

    stage = "IMPORT_CONFIRMATION";
    await click("Privacy & updates");
    const advanced = await until(() =>
      [...document.querySelectorAll("summary")].find(
        (node) => node.textContent === "Advanced: import a legacy workspace",
      ),
    );
    advanced.click();
    await click("Import original workspace");
    await until(() => document.querySelector('[role="dialog"]'));
    await click("Cancel");
    await until(() => !document.querySelector('[role="dialog"]'));
    await checkpoint(stage);

    stage = "ACTIVITY";
    (
      await until(() =>
        [...document.querySelectorAll("button")].find((node) =>
          name(node).startsWith("Background activity"),
        ),
      )
    ).click();
    await until(() => document.querySelector(".activity-page"));
    await checkpoint(stage);
    await click("Articles");
    await until(() => document.querySelector(".article-filters"));

    const savedNews = await call("news.list", { limit: 1 });
    if (savedNews.articles.length) {
      stage = "ARTICLE_READING";
      const card = await until(() => document.querySelector(".article-open"));
      card.click();
      await until(
        () =>
          document.querySelector(".reader-content .prose")?.textContent.length >
          80,
      );
      await checkpoint(stage);
      stage = "ARTICLE_LIBRARY_NAV";
      await click("Articles");
      await until(() => document.querySelector(".article-filters"));
      (await until(() => document.querySelector(".article-open"))).click();
      await until(
        () =>
          document.querySelector(".reader-content .prose")?.textContent.length >
          80,
      );
      await checkpoint(stage);
      stage = "ARTICLE_REPORT";
      await click("Report this article");
      const report = await until(
        () => document.querySelector(".support-dialog pre")?.textContent,
      );
      assert(
        report.includes("## Article context") && report.includes("https://"),
      );
      await click("Save diagnostic report");
      const savedReport = await until(() =>
        document
          .querySelector(".saved-report")
          ?.textContent.match(/openNews-diagnostics-([0-9a-f-]+)\.txt/),
      );
      await checkpoint("REPORT_SAVED_" + savedReport[1]);
      await click("Close");
      await until(() => !document.querySelector(".support-dialog"));
      await checkpoint(stage);
      stage = "ORIGINAL_SITE";
      const before = window.__openNewsQaSiteLoads || 0;
      await click("Original website");
      await until(() => (window.__openNewsQaSiteLoads || 0) > before);
      await checkpoint(stage);
      await click("Reading");
      await until(() =>
        document.querySelector(".reader-content:not([hidden])"),
      );
      document.querySelector(".reader-toolbar button").click();
      await until(() => document.querySelector(".article-filters"));
    } else {
      await checkpoint("EMPTY_ARTICLE_LIBRARY");
    }

    stage = "SIDEBAR";
    await click("Hide sidebar");
    await until(() => document.querySelector(".app.collapsed"));
    await click("Show sidebar");
    await until(() => !document.querySelector(".app.collapsed"));
    await checkpoint(stage);
    if (savedNews.articles.length) {
      stage = "SITE_PREVIEW";
      (await until(() => document.querySelector(".article-open"))).click();
      await until(
        () =>
          document.querySelector(".reader-content .prose")?.textContent.length >
          80,
      );
      const before = window.__openNewsQaSiteLoads || 0;
      await click("Original website");
      await until(() => (window.__openNewsQaSiteLoads || 0) > before);
      await checkpoint(stage);
    }
    if (savedNews.articles.length) {
      await click("Reading");
      await until(() => document.querySelector(".reader-content:not([hidden])"));
      document.querySelector(".reader-toolbar button").click();
      await until(() => document.querySelector(".article-filters"));
    }
    await click("Settings");
    await click("Local models");
    await until(() => document.querySelector(".processing-pause button:not(:disabled)"));
    await checkpoint("SETTINGS_LOCAL_MODELS_RENDERED");
    stage = "SHARED_OLLAMA_LIBRARY";
    const installedModels = (await call("news.local.available", { capability: "" })).installed;
    const modelSearch = await until(() => document.querySelector('.model-search input'));
    await until(() => document.querySelector('.model-list[aria-busy="false"]'));
    assert(document.querySelectorAll('.model-browser').length === 1);
    for (const model of installedModels) assert([...document.querySelectorAll('.model-result')].some((node) => node.textContent.includes(model.id)));
    enter(modelSearch, installedModels[0]?.id || "shared-library-check");
    const originalQuery = modelSearch.value;
    document.querySelectorAll('.model-role-trigger')[0].click();
    await pause();
    document.querySelectorAll('.model-role-trigger')[1].click();
    await pause();
    assert(document.querySelector('.model-search input') === modelSearch && modelSearch.value === originalQuery);
    enter(modelSearch, "");
    await click("Ollama library");
    await pause();
    await until(() => document.querySelector('.model-list[aria-busy="false"] .model-result'));
    for (const row of document.querySelectorAll('.model-result')) {
      assert(row.getBoundingClientRect().height >= 72);
      assert(row.scrollHeight <= row.clientHeight + 1);
    }
    await checkpoint(stage);
    stage = "INLINE_MODEL_CHOICE";
    await click("Article search");
    (await until(() => document.querySelector('.manage-local-models'))).click();
    const inlineSearch = await until(() => document.querySelector('#article-model-picker .model-search input'));
    enter(inlineSearch, "keep my model search");
    stage = "INLINE_MODEL_CONTEXT";
    assert(sessionStorage.getItem("settings-tab") === "search");
    stage = "INLINE_MODEL_FOCUS";
    inlineSearch.focus();
    await pause();
    assert(getComputedStyle(inlineSearch).outlineStyle === "none");
    assert(getComputedStyle(inlineSearch.closest('label')).outlineWidth === "2px");
    await checkpoint(stage);
    await click("Writing skills");
    await until(() => document.querySelector(".skill-rows button"));
    await click("Discover skills");
    await until(() => document.querySelector(".discovery-rows > div"));
    await checkpoint("SETTINGS_SKILL_DISCOVERY_RENDERED");
    stage = "SETTINGS_CONTROL_DETAILS";
    await click("Appearance & language");
    const currentPreference = await until(() => document.querySelector('.settings-subnav button[aria-current="page"]'));
    const currentStyle = getComputedStyle(currentPreference);
    assert(currentPreference.textContent === "Appearance & language");
    assert(!currentPreference.classList.contains("selected"));
    assert(parseFloat(currentStyle.paddingInlineStart) >= 12);
    assert(currentPreference.getBoundingClientRect().height >= 40);
    assert(currentStyle.backgroundColor === "rgba(0, 0, 0, 0)");
    currentPreference.focus();
    assert(document.activeElement === currentPreference);
    await click("Privacy & updates");
    await until(() => document.querySelector('.settings-subnav button[aria-current="page"]')?.textContent === "Privacy & updates");
    await click("Appearance & language");
    await until(() => document.querySelector('.settings-subnav button[aria-current="page"]')?.textContent === "Appearance & language");
    document.activeElement?.blur();
    await checkpoint(stage);
    await click("Local models");
    await click("Ollama library");
    await pause();
    await until(() => document.querySelector('.model-list[aria-busy="false"] .model-result'));
    await checkpoint("MODEL_LIBRARY_RENDERED");
    await checkpoint("PASSED");
  } catch (error) {
    console.error("Native QA", stage, error);
    await checkpoint("FAILED_" + stage);
  }
})();
