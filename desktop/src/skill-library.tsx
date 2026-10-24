import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  ChevronDown,
  ExternalLink,
  Link,
  LoaderCircle,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { invoke } from "@tauri-apps/api/core";
import { call, type RecordData } from "./engine";
import { t, useLocale } from "./locale";
import { TaskInstructions } from "./task-instructions";
import { navigateSafely, useUnsavedChanges } from "./unsaved-changes";
import { settingsMessage } from "./settings-message";

const topics = [
  ["Article writing", "article writing"],
  ["Research", "research sources"],
  ["Social posts", "social media writing"],
  ["Newsletters", "newsletter writing"],
];
export function SkillLibrary({
  onUse,
  onRecommend,
}: {
  onUse?: (id: string) => void;
  onRecommend?: () => void;
}) {
  const locale = useLocale();
  const [view, setView] = useState<"library" | "discover">("library");
  const [rows, setRows] = useState<RecordData[]>([]),
    [loading, setLoading] = useState(true),
    [loadError, setLoadError] = useState("");
  const [query, setQuery] = useState(""),
    [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState<RecordData[]>([]),
    [searched, setSearched] = useState(false),
    [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<RecordData | null>(null);
  const [linkOpen, setLinkOpen] = useState(false),
    [url, setUrl] = useState("");
  const [preview, setPreview] = useState<RecordData | null>(null),
    [collection, setCollection] = useState<RecordData[]>([]);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false),
    [reading, setReading] = useState(false),
    [removing, setRemoving] = useState(false);
  const live = useRef(true),
    request = useRef(0),
    searchRequest = useRef(0),
    lock = useRef(false);
  const importBaseline = useRef("");
  const surface = useRef<HTMLElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const previewHeading = useRef<HTMLHeadingElement>(null);
  const linkInput = useRef<HTMLInputElement>(null);
  const addLink = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef({ kind: "link", value: "" });
  const pendingFocus = useRef("heading");
  const [focusVersion, setFocusVersion] = useState(0);
  function moveFocus(destination: string) {
    pendingFocus.current = destination;
    setFocusVersion((version) => version + 1);
  }
  useEffect(() => {
    if (!focusVersion) return;
    const destination = pendingFocus.current;
    const origin = returnFocus.current;
    const row =
      destination === "return"
        ? Array.from(
            surface.current?.querySelectorAll<HTMLButtonElement>(
              "[data-skill-id], [data-skill-source]",
            ) || [],
          ).find((element) =>
            origin.kind === "library"
              ? element.dataset.skillId === origin.value
              : element.dataset.skillSource === origin.value,
          )
        : null;
    const target =
      destination === "detail"
        ? detailHeading.current
        : destination === "preview"
          ? previewHeading.current
          : destination === "url"
            ? linkInput.current
            : destination === "return"
              ? row || addLink.current
              : destination === "link"
                ? addLink.current
                : heading.current;
    (target || heading.current)?.focus();
  }, [focusVersion]);
  const guard = useUnsavedChanges(
    Boolean(preview) && JSON.stringify(preview) !== importBaseline.current,
    add,
  );
  const label = (row: RecordData, field: string) =>
    row[`${field}_${locale}`] || row[field] || row.id;
  async function load() {
    setLoading(true);
    setLoadError("");
    try {
      const result = await call("skills.catalog");
      if (live.current) setRows(result.skills || []);
    } catch (reason) {
      if (live.current) setLoadError(settingsMessage(String(reason)));
    } finally {
      if (live.current) setLoading(false);
    }
  }
  useEffect(() => {
    live.current = true;
    void load();
    return () => {
      live.current = false;
      request.current++;
      searchRequest.current++;
    };
  }, []);
  async function search(value: string, display = value) {
    const token = ++searchRequest.current;
    setSearchQuery(display);
    setSearching(true);
    setError("");
    setSearched(true);
    setResults([]);
    try {
      const result = await call("skills.search", {
        query:
          topics.find(([title]) => t(title) === value.trim())?.[1] ||
          value.trim() ||
          "content writing",
      });
      if (live.current && token === searchRequest.current)
        setResults(result.skills || []);
    } catch (reason) {
      if (live.current && token === searchRequest.current)
        setError(settingsMessage(String(reason)));
    } finally {
      if (live.current && token === searchRequest.current) setSearching(false);
    }
  }
  function switchView(next: "library" | "discover") {
    navigateSafely(() => {
      request.current++;
      setReading(false);
      setView(next);
      setSelected(null);
      setPreview(null);
      setCollection([]);
      setError("");
      setNotice("");
      if (next === "discover" && !searched)
        void search("article writing", t("Article writing"));
    });
  }
  async function inspect(address: string) {
    if (reading || busy) return;
    const token = ++request.current;
    setReading(true);
    setError("");
    setNotice("");
    if (!collection.length)
      returnFocus.current = linkOpen
        ? { kind: "link", value: "" }
        : { kind: "discover", value: address };
    setCollection([]);
    try {
      const result = await call("skills.preview", { url: address.trim() });
      if (!live.current || token !== request.current) return;
      if (result.kind === "collection") setCollection(result.skills || []);
      else {
        let id = result.id.length < 2 ? `${result.id}-guide` : result.id;
        let suffix = 2;
        while (rows.some((row) => row.id === id))
          id = `${result.id.slice(0, 35)}-${suffix++}`;
        const proposal = { ...result, id };
        importBaseline.current = JSON.stringify(proposal);
        setPreview(proposal);
        setLinkOpen(false);
        moveFocus("preview");
      }
    } catch (reason) {
      if (live.current && token === request.current)
        setError(settingsMessage(String(reason)));
    } finally {
      if (live.current && token === request.current) setReading(false);
    }
  }
  async function add() {
    if (!preview || lock.current) return false;
    if (
      !preview.title?.trim() ||
      !preview.description?.trim() ||
      !/^[a-z][a-z0-9-]{1,39}$/.test(preview.id) ||
      !preview.content?.trim() ||
      preview.content.length > 12000
    ) {
      setError(
        t(
          "Add a name, description and a unique command. Instructions can contain up to 12,000 characters.",
        ),
      );
      return false;
    }
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      await call("skills.add", preview);
      if (!live.current) return true;
      const item = {
        ...preview,
        title_ar: preview.title,
        title_en: preview.title,
        description_ar: preview.description,
        description_en: preview.description,
        origin: "custom",
      };
      setRows((old) => [...old, item]);
      setPreview(null);
      setCollection([]);
      setSelected(item);
      setView("library");
      returnFocus.current = { kind: "library", value: preview.id };
      moveFocus("detail");
      setNotice(t("Skill added. It is ready for your next conversation."));
      return true;
    } catch (reason) {
      if (live.current) setError(settingsMessage(String(reason)));
      return false;
    } finally {
      lock.current = false;
      if (live.current) setBusy(false);
    }
  }
  function back() {
    navigateSafely(() => {
      setSelected(null);
      setPreview(null);
      setCollection([]);
      setError("");
      moveFocus("return");
    });
  }
  async function remove() {
    if (!selected || lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      await call("skills.remove", { id: selected.id });
      setRows((old) => old.filter((row) => row.id !== selected.id));
      setSelected(null);
      setRemoving(false);
      setNotice(t("Skill removed from your library."));
      moveFocus("heading");
    } catch (reason) {
      setError(settingsMessage(String(reason)));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  const Back = locale === "ar" ? ArrowRight : ArrowLeft;
  const filtered = rows.filter((row) =>
    `${label(row, "title")} ${label(row, "description")} ${row.id}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  async function openSource(address: string) {
    try {
      await invoke("open_external", { address });
    } catch (reason) {
      setError(settingsMessage(String(reason)));
    }
  }
  return (
    <section className="skill-library" ref={surface}>
      {guard.dialog}
      <header className="skill-library-heading">
        <div>
          <h2 ref={heading} tabIndex={-1}>
            {t("Writing skills")}
          </h2>
          <p className="muted">
            {t(
              "Give your assistant a useful way to write, research or explain.",
            )}
          </p>
        </div>
        {!selected && !preview && (
          <button
            className="primary"
            ref={addLink}
            onClick={() => {
              setLinkOpen(true);
              setError("");
              moveFocus("url");
            }}
          >
            <Plus size={15} />
            {t("Add from a link")}
          </button>
        )}
      </header>
      {notice && (
        <p className="inline-success" role="status">
          <Check size={15} />
          {notice}
        </p>
      )}
      {error && (
        <div className="settings-feedback" role="alert">
          <span>{error}</span>
          <button onClick={() => setError("")}>{t("Dismiss")}</button>
        </div>
      )}
      {selected ? (
        <>
          <button className="skill-back" onClick={back}>
            <Back size={16} />
            {t("Back to your skills")}
          </button>
          <div className="skill-detail-heading">
            <div>
              <h3 dir="auto" ref={detailHeading} tabIndex={-1}>
                {label(selected, "title")}
              </h3>
              <p className="muted" dir="auto">
                {label(selected, "description")}
              </p>
              <code dir="ltr">/{selected.id}</code>
            </div>
            {onUse && (
              <button className="primary" onClick={() => onUse(selected.id)}>
                {t("Try in a conversation")}
              </button>
            )}
          </div>
          <p className="skill-usage">
            {t(
              "Describe what you need, or start your message with this command. The assistant loads the instructions when it uses the skill.",
            )}
          </p>
          {selected.source_url && (
            <button
              className="skill-source"
              onClick={() => void openSource(selected.source_url)}
            >
              <ExternalLink size={14} />
              <bdi>{selected.repository || t("Original source")}</bdi>
            </button>
          )}
          <TaskInstructions
            key={selected.id}
            id={`skill:${selected.id}`}
            title={t("Skill instructions")}
            onError={setError}
          />
          {selected.origin === "custom" && (
            <button
              className="skill-remove"
              onClick={() => navigateSafely(() => setRemoving(true))}
            >
              <Trash2 size={14} />
              {t("Remove skill")}
            </button>
          )}
        </>
      ) : preview ? (
        <>
          <button className="skill-back" disabled={busy} onClick={back}>
            <Back size={16} />
            {t(
              view === "library" ? "Back to your skills" : "Back to discovery",
            )}
          </button>
          <h3 ref={previewHeading} tabIndex={-1}>
            {t("Review before adding")}
          </h3>
          <div className="skill-import-source">
            <BookOpen size={19} />
            <span>
              <strong>
                <bdi>{preview.repository}</bdi>
              </strong>
              <small>
                {t(
                  "A local copy of the writing instructions. Scripts and extra tools are not installed.",
                )}
              </small>
            </span>
            <button
              className="icon-button"
              aria-label={t("Original source")}
              onClick={() => void openSource(preview.source_url)}
            >
              <ExternalLink size={16} />
            </button>
          </div>
          {(preview.supporting_files || preview.requires_tools) && (
            <p className="notice">
              {t(
                "This source also includes files or tools. openNews uses the main instructions only; steps that depend on those extras may not work.",
              )}
            </p>
          )}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void add();
            }}
          >
            <fieldset className="plain-fieldset" disabled={busy}>
              <div className="form-grid">
                <label className="field">
                  {t("Skill name")}
                  <input
                    required
                    maxLength={100}
                    dir="auto"
                    value={preview.title}
                    onChange={(event) =>
                      setPreview({ ...preview, title: event.target.value })
                    }
                  />
                </label>
                <label className="field">
                  {t("Command")}
                  <span className="skill-command-input">
                    <span aria-hidden="true">/</span>
                    <input
                      required
                      dir="ltr"
                      pattern="[a-z][a-z0-9-]{1,39}"
                      maxLength={40}
                      value={preview.id}
                      onChange={(event) =>
                        setPreview({ ...preview, id: event.target.value })
                      }
                    />
                  </span>
                </label>
              </div>
              <label className="field">
                {t("When to use it")}
                <textarea
                  required
                  maxLength={300}
                  dir="auto"
                  rows={2}
                  value={preview.description}
                  onChange={(event) =>
                    setPreview({ ...preview, description: event.target.value })
                  }
                />
              </label>
              <details className="skill-instruction-preview">
                <summary>
                  {t("Read or adjust instructions")}
                  <ChevronDown size={15} />
                </summary>
                <textarea
                  className="editor"
                  dir="auto"
                  aria-label={t("Imported instructions")}
                  value={preview.content}
                  onChange={(event) =>
                    setPreview({ ...preview, content: event.target.value })
                  }
                />
              </details>
              <div className="skill-add-footer">
                <small
                  className={
                    preview.content.length > 12000 ? "error-text" : "muted"
                  }
                >
                  <bdi>{preview.content.length.toLocaleString()} / 12,000</bdi>{" "}
                  {t("characters")}
                  {preview.license && (
                    <>
                      {" "}
                      · <bdi>{preview.license}</bdi>
                    </>
                  )}
                </small>
                <button
                  className="primary"
                  disabled={
                    busy ||
                    preview.content.length > 12000 ||
                    !preview.content.trim()
                  }
                >
                  {busy ? (
                    <LoaderCircle size={15} className="spin" />
                  ) : (
                    <Plus size={15} />
                  )}
                  {t(busy ? "Adding skill…" : "Add to your skills")}
                </button>
              </div>
            </fieldset>
          </form>
        </>
      ) : (
        <>
          <div
            className="segments skill-library-tabs"
            role="group"
            aria-label={t("Skill library")}
          >
            <button
              className={view === "library" ? "selected" : ""}
              aria-pressed={view === "library"}
              onClick={() => switchView("library")}
            >
              {t("Your skills")}
            </button>
            <button
              className={view === "discover" ? "selected" : ""}
              aria-pressed={view === "discover"}
              onClick={() => switchView("discover")}
            >
              {t("Discover skills")}
            </button>
          </div>
          {linkOpen && (
            <form
              className="skill-link-form"
              onSubmit={(event) => {
                event.preventDefault();
                void inspect(url);
              }}
            >
              <div className="editor-header">
                <h3>{t("Add from GitHub or skills.sh")}</h3>
                <button
                  className="icon-button"
                  type="button"
                  aria-label={t("Close link form")}
                  onClick={() => {
                    request.current++;
                    setReading(false);
                    setLinkOpen(false);
                    moveFocus("link");
                  }}
                >
                  <X size={16} />
                </button>
              </div>
              <label className="field">
                {t("Skill or repository link")}
                <input
                  type="url"
                  ref={linkInput}
                  required
                  dir="ltr"
                  placeholder="https://github.com/owner/repo"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                />
              </label>
              <p className="muted">
                {t(
                  "Paste a skill file, folder or repository. You can choose a skill if the repository contains several.",
                )}
              </p>
              <button className="primary" disabled={reading}>
                {reading ? (
                  <LoaderCircle size={14} className="spin" />
                ) : (
                  <Link size={14} />
                )}
                {t(reading ? "Reading skill…" : "Preview skill")}
              </button>
            </form>
          )}
          {collection.length > 0 && (
            <section className="skill-collection">
              <h3>{t("Choose a skill from this repository")}</h3>
              {collection.map((row) => (
                <button
                  key={row.id}
                  disabled={reading}
                  onClick={() => void inspect(row.source_url)}
                >
                  <BookOpen size={16} />
                  <bdi>{row.title}</bdi>
                  <span>{t("Preview")}</span>
                </button>
              ))}
            </section>
          )}
          {view === "library" ? (
            <>
              <label className="skill-search">
                <Search size={16} />
                <input
                  aria-label={t("Search your skills")}
                  placeholder={t("Search your skills")}
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
              {loading ? (
                <p role="status" className="inline-loading">
                  <LoaderCircle size={15} className="spin" />
                  {t("Loading skills…")}
                </p>
              ) : loadError ? (
                <div role="alert">
                  <p>{loadError}</p>
                  <button onClick={() => void load()}>{t("Try again")}</button>
                </div>
              ) : (
                <>
                  {filtered.length ? (
                    <div className="skill-rows">
                      {filtered.map((row) => (
                        <button
                          key={row.id}
                          data-skill-id={row.id}
                          aria-label={label(row, "title")}
                          onClick={() => {
                            returnFocus.current = {
                              kind: "library",
                              value: row.id,
                            };
                            setSelected(row);
                            setNotice("");
                            moveFocus("detail");
                          }}
                        >
                          <span>
                            <strong dir="auto">{label(row, "title")}</strong>
                            <small dir="auto">
                              {label(row, "description")}
                            </small>
                          </span>
                          <span className="skill-row-meta">
                            <code dir="ltr">/{row.id}</code>
                            <small>
                              {t(
                                row.origin === "custom"
                                  ? "Added by you"
                                  : "Included with openNews",
                              )}
                            </small>
                          </span>
                          <ChevronDown size={15} />
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="skill-empty">
                      <BookOpen size={25} />
                      <h3>
                        {t(
                          query
                            ? "No skills match your search."
                            : "Make your assistant more useful",
                        )}
                      </h3>
                      <p>
                        {t(
                          "Discover writing and research skills, then review one before adding it.",
                        )}
                      </p>
                      <button onClick={() => switchView("discover")}>
                        {t("Discover skills")}
                      </button>
                    </div>
                  )}
                  <p className="preference-footnote">
                    {t(
                      "Your skills are ready to use. No model download is needed to add a skill.",
                    )}
                  </p>
                </>
              )}
            </>
          ) : (
            <>
              <p className="skill-discovery-intro">
                {t(
                  "Find ideas for your writing and research. Results come live from skills.sh; preview the original GitHub instructions before adding.",
                )}
              </p>
              {onRecommend && (
                <button className="skill-recommend" onClick={onRecommend}>
                  {t("Ask the assistant to suggest useful skills")}
                  <ArrowRight size={14} />
                </button>
              )}
              <form
                className="skill-search-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void search(searchQuery);
                }}
              >
                <label className="skill-search">
                  <Search size={16} />
                  <input
                    aria-label={t("Search online skills")}
                    placeholder={t("What would you like help with?")}
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                  />
                </label>
                <button disabled={searching}>{t("Search")}</button>
              </form>
              <div className="skill-topics" aria-label={t("Suggested topics")}>
                {topics.map(([title, value]) => (
                  <button
                    key={value}
                    aria-pressed={
                      searchQuery === value || searchQuery === t(title)
                    }
                    onClick={() => void search(value, t(title))}
                  >
                    {t(title)}
                  </button>
                ))}
              </div>
              {searching ? (
                <p className="inline-loading" role="status">
                  <LoaderCircle size={15} className="spin" />
                  {t("Finding skills…")}
                </p>
              ) : results.length ? (
                <div className="skill-rows discovery-rows">
                  {results.map((row) => (
                    <div key={row.id}>
                      <span>
                        <strong dir="auto">{row.title}</strong>
                        <small>
                          <bdi>{row.repository}</bdi>
                        </small>
                      </span>
                      <button
                        data-skill-source={row.source_url}
                        disabled={reading}
                        onClick={() => void inspect(row.source_url)}
                      >
                        {t("Preview skill")}
                      </button>
                    </div>
                  ))}
                </div>
              ) : searched && !error ? (
                <p className="skill-empty">
                  {t(
                    "No skills found. Try another topic or paste a GitHub link.",
                  )}
                </p>
              ) : null}
              {reading && (
                <p className="inline-loading" role="status">
                  <LoaderCircle size={15} className="spin" />
                  {t("Reading skill…")}
                </p>
              )}
              <div className="skill-directory-link">
                <span>
                  {t("Found a skill on another website?")}
                  <small>
                    {t("Copy its original GitHub link and add it here.")}
                  </small>
                </span>
                <button onClick={() => void openSource("https://skills.sh/")}>
                  {t("Browse skills.sh")}
                  <ExternalLink size={14} />
                </button>
              </div>
            </>
          )}
        </>
      )}
      <Dialog.Root
        open={removing}
        onOpenChange={(open) => {
          if (!busy) setRemoving(open);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-panel">
            <Dialog.Title>{t("Remove this skill?")}</Dialog.Title>
            <Dialog.Description>
              {t(
                "It will leave your library and command menu. Existing conversations and drafts stay saved.",
              )}
            </Dialog.Description>
            <div className="dialog-actions">
              <button disabled={busy} onClick={() => setRemoving(false)}>
                {t("Cancel")}
              </button>
              <button disabled={busy} onClick={() => void remove()}>
                {t(busy ? "Removing…" : "Remove skill")}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  );
}
