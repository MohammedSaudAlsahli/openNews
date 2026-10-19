import { useEffect, useState, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { issueUrl, articleIncidentText, type ArticleIncident } from "./support-report";
import { t } from "./locale";
export function SupportPanel({onClose,onError,incidentCode="",article}:{onClose:()=>void;onError:(e:string)=>void;incidentCode?:string;article?:ArticleIncident}) {
  const [report,setReport]=useState(""); const [saved,setSaved]=useState("");
  const [includeArticle,setIncludeArticle]=useState(true);
  const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{dialog.current?.showModal();void invoke<string>("diagnostics_report").then(setReport).catch(e=>onError(String(e)))},[]);
  return <dialog ref={dialog} className="support-dialog" onCancel={onClose}>
    <div className="page-title"><h2>{t("Help & diagnostics")}</h2><button autoFocus onClick={onClose} aria-label={t("Close")}>×</button></div>
    <p>{t("Technical events stay on this Mac. Reports exclude messages, article contents, account names and credentials.")}</p>
    {article && <label><input type="checkbox" checked={includeArticle} onChange={e=>setIncludeArticle(e.target.checked)}/>{t("Include article title, public URL and loading details in this report")}</label>}
    <div className="shortcut-list">
      <span>{t("Settings")}</span><kbd>⌘ ,</kbd><span>{t("New conversation")}</span><kbd>⌘ N</kbd>
      <span>{t("Toggle sidebar")}</span><kbd>⌘ ⇧ B</kbd><span>{t("Commands / articles")}</span><kbd>/ · @</kbd>
      <span>{t("New line")}</span><kbd>⇧ Enter</kbd>
    </div>
    <details open><summary>{t("Review diagnostic report")}</summary><pre>{article && includeArticle ? articleIncidentText(article) + "\n" : ""}{incidentCode && `Incident: ${incidentCode}\n`}{report || t("Loading…")}</pre></details>
    <div className="reader-actions"><button onClick={()=>void invoke<string>("export_diagnostics").then(setSaved).catch(e=>onError(String(e)))}>{t("Save diagnostic report")}</button>
    <button disabled={!report} className="primary" onClick={()=>void invoke("open_external",{address:issueUrl(report, incidentCode, includeArticle ? article : undefined)}).catch(e=>onError(String(e)))}>{t("Report a problem on GitHub")}</button></div>
    {saved&&<p role="status">{t("Saved")}: {saved}</p>}
    <small>{t("GitHub opens a draft report. Review it and submit it yourself.")}</small>
  </dialog>;
}
