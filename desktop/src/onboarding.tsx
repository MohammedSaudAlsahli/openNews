import { t } from "./locale";
export function Onboarding({
  go,
  close,
}: {
  go: (page: string) => void;
  close: () => void;
}) {
  return (
    <section
      className="welcome-guide"
      role="region"
      aria-label={t("Getting started")}
    >
      <h1>{t("Set up openNews")}</h1>
      <p>
        {t(
          "Follow your sources to start reading. Add a model whenever you want explanations or conversation.",
        )}
      </p>
      <div className="reader-actions">
        <button
          className="primary"
          onClick={() => {
            close();
            go("sources");
          }}
        >
          {t("Explore sources")}
        </button>
        <button
          onClick={() => {
            sessionStorage.setItem("settings-tab", "connections");
            close();
            go("settings");
          }}
        >
          {t("Connect a model")}
        </button>
        <button onClick={close}>{t("Skip for now")}</button>
      </div>
    </section>
  );
}
