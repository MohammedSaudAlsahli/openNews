import { Search, LoaderCircle } from "lucide-react";
import type { RecordData } from "./engine";
import { t } from "./locale";

function bucket(value:string) {
  const day=new Date();day.setHours(0,0,0,0);
  const stamp=new Date(value).getTime();
  const elapsed=(day.getTime()-stamp)/86400000;
  if(elapsed<=0)return "Today";
  if(elapsed<=1)return "Yesterday";
  if(elapsed<=7)return "Previous 7 days";
  return "Earlier conversations";
}
export function ConversationList({chats,selected,search,onSearch,onChoose}:{chats:RecordData[];selected:string;search:string;onSearch:(s:string)=>void;onChoose:(id:string)=>void}) {
  const filtered=chats.filter(c=>String(c.title).toLowerCase().includes(search.toLowerCase()));
  const groups=filtered.reduce<Record<string,RecordData[]>>((result,c)=>{const key=bucket(c.updated_at);(result[key]||=[]).push(c);return result},{});
  return <>
    <div className="chat-heading">{t("Conversations")}</div>
    <label className="sidebar-search"><Search size={14}/><input aria-label={t("Search conversations")} placeholder={t("Search conversations")} value={search} onChange={e=>onSearch(e.target.value)}/></label>
    <div className="chat-list" aria-label={t("Conversations")}>
      {!filtered.length&&<p className="sidebar-empty">{t(search?"No conversations match your search":"Your conversations will appear here.")}</p>}
      {Object.entries(groups).map(([group,rows])=><section className="conversation-group" key={group}><h2>{t(group)}</h2>{rows.map(c=><button key={c.id} title={c.title} className={selected===c.id?"selected":""} aria-current={selected===c.id?"page":undefined} onClick={()=>onChoose(c.id)}><span dir="auto">{c.title}</span>{c.active_job_id&&<LoaderCircle size={13} className="spin"/>}</button>)}</section>)}
    </div>
  </>;
}
