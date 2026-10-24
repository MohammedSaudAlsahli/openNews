import { invoke } from "@tauri-apps/api/core";
import { issueUrl } from "./support-report";

// Module failures happen before React can mount. Always leave
// a usable recovery screen instead of a blank native webview.
void import("./main").catch((error: unknown) => {
  const root = document.getElementById("root");
  if (!root) return;
  let arabic = document.documentElement.lang === "ar";
  try {
    arabic ||= localStorage.getItem("interface-language") === "ar";
  } catch {
    /* Recovery must also work when storage is unavailable. */
  }
  const panel = document.createElement("main");
  panel.style.cssText =
    "max-width:560px;margin:15vh auto;padding:32px;font:16px/1.7 system-ui;color:#1c1c1c;background:#fff;border-radius:12px";
  panel.setAttribute("role", "alert");
  panel.dir = arabic ? "rtl" : "ltr";
  const heading = document.createElement("h1");
  heading.style.fontSize = "24px";
  heading.textContent = arabic
    ? "تعذّر تحميل واجهة openNews"
    : "openNews could not load its interface";
  const explanation = document.createElement("p");
  explanation.textContent = arabic
    ? "أعد تحميل الواجهة للمحاولة مجددًا. لم تُحذف بياناتك المحفوظة."
    : "Reload the interface to try again. Your saved workspace has not been deleted.";
  const detail = document.createElement("pre");
  detail.style.cssText =
    "white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;direction:ltr;text-align:left";
  detail.textContent =
    error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  const reload = document.createElement("button");
  reload.textContent = arabic ? "إعادة التحميل" : "Reload interface";
  reload.style.cssText = "padding:10px 18px;font:inherit;cursor:pointer";
  reload.addEventListener("click", () => location.reload());
  const report = document.createElement("button");
  report.textContent = arabic ? "الإبلاغ عن المشكلة" : "Report this problem";
  report.style.cssText = reload.style.cssText;
  report.addEventListener("click", async () => {
    report.disabled = true;
    try {
      const diagnostics = await invoke<string>("diagnostics_report");
      await invoke("open_external", {
        address: issueUrl(diagnostics, "UI_LOAD_FAILED"),
      });
    } catch {
      explanation.textContent = arabic
        ? "تعذّر فتح التقرير. حاول إعادة التحميل أولًا."
        : "The report could not open. Try reloading the interface first.";
    } finally {
      report.disabled = false;
    }
  });
  panel.append(heading, explanation, detail, reload, report);
  root.replaceChildren(panel);
  void invoke("record_diagnostic", {
    operation: "frontend.bootstrap",
    code: "UI_LOAD_FAILED",
  }).catch(() => {});
});
