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
      <h2>{t("Your news, your workspace.")}</h2>
      <p>
        {t(
          "Read articles immediately. Connect a model when you want explanations and conversation.",
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
