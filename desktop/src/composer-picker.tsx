import { useEffect, useState } from "react";
import { call, type RecordData } from "./engine";
import { t } from "./locale";
export const commands = [
  ["research", "Research a topic with sources"], ["summarize", "Explain an article in detail"],
  ["x", "Write a post for X"], ["thread", "Turn an idea into a thread"],
  ["shorts", "Write a short video script"], ["hooks", "Suggest opening lines"],
  ["linkedin", "Write a LinkedIn post"], ["youtube", "Write a YouTube script"],
  ["rewrite", "Improve your writing"], ["plan", "Create a content plan"],
];
export function ComposerPicker({message, onMessage, onArticle, onError}: {
  message: string; onMessage: (value:string)=>void; onArticle:(row:RecordData)=>void; onError:(message:string)=>void;
}) {
  const slash = /^\/([\w-]*)$/.exec(message);
  const mention = /(?:^|\s)@([^@\n]*)$/.exec(message);
  const query = mention?.[1] || "";
  const [rows,setRows] = useState<RecordData[]>([]);
  const [busy,setBusy] = useState(false);
  const [index,setIndex] = useState(0);
  const [dismissed,setDismissed] = useState<string>();
  const [bookmarks,setBookmarks] = useState(false);
  useEffect(()=>{setIndex(0)},[message,bookmarks]);
  useEffect(()=>{
    if(!mention) return;
    let live=true; setBusy(true); setRows([]);
    const timer=setTimeout(()=>void call("news.list",{query:query.slice(0,200),limit:12,...(bookmarks?{scope:"saved"}:{})})
      .then(r=>{if(live)setRows(r.articles||[])})
      .catch(e=>{if(live)onError(String(e))})
      .finally(()=>{if(live)setBusy(false)}),200);
    return ()=>{live=false;clearTimeout(timer)};
  },[query,Boolean(mention),bookmarks]);
  const choices: RecordData[] = slash ? commands.filter(([name])=>name.startsWith(slash[1])).map(([id,description])=>({id,title:`/${id}`,description})) : rows;
  const visible=Boolean(slash||mention)&&dismissed!==message;
  function pick(row:RecordData){
    if(slash)onMessage(`/${row.id} `);
    else {onArticle(row);onMessage(message.slice(0,message.lastIndexOf("@")).trimEnd());}
  }
  useEffect(()=>{
    if(!visible)return;
    const handler=(e:KeyboardEvent)=>{
      if(!(e.target instanceof HTMLTextAreaElement)||e.isComposing)return;
      if(["ArrowDown","ArrowUp","Escape","Enter"].includes(e.key)){
        e.preventDefault();e.stopImmediatePropagation();
        if(e.key==="Escape")setDismissed(message);
        else if(e.key==="Enter"){if(choices[index])pick(choices[index]);}
        else setIndex(i=>choices.length?(i+(e.key==="ArrowDown"?1:-1)+choices.length)%choices.length:0);
      }
    };
    window.addEventListener("keydown",handler,true);
    return ()=>window.removeEventListener("keydown",handler,true);
  },[visible,message,index,choices]);
  useEffect(()=>{document.getElementById(`composer-option-${index}`)?.scrollIntoView({block:"nearest"})},[index]);
  if(!visible)return null;
  return <section className="composer-picker" aria-label={t(slash?"Commands":"Choose an article")}>
    <div className="picker-heading"><strong>{t(slash?"Commands":"Choose an article")}</strong><small>↑ ↓ · Enter · Esc</small></div>
    {mention&&<div className="segments"><button type="button" aria-pressed={!bookmarks} onClick={()=>setBookmarks(false)}>{t("All")}</button><button type="button" aria-pressed={bookmarks} onClick={()=>setBookmarks(true)}>{t("Bookmarks")}</button></div>}
    <div className="picker-results" role="listbox">
      {choices.map((row,i)=><button type="button" role="option" aria-selected={i===index} id={`composer-option-${i}`} key={row.id} onMouseEnter={()=>setIndex(i)} onClick={()=>pick(row)}>
        <strong dir="auto">{row.title}</strong><small dir="auto">{slash?t(row.description):row.source_title}</small>
      </button>)}
      {!choices.length&&<p role="status">{t(busy?"Searching…":"No matches")}</p>}
    </div>
  </section>;
}
