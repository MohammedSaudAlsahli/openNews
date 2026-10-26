import { useState } from "react";
import { Search, X, Check, ChevronRight } from "lucide-react";
import { t } from "./locale";
import type { RecordData } from "./engine";

const families: [string, string[]][] = [
  ["OpenAI", ["openai-chatgpt", "openai", "openai-chat", "openai-responses"]],
  ["Claude", ["anthropic"]],
  ["Gemini", ["google", "google-oauth", "google-interactions"]],
  ["Ollama", ["ollama", "ollama-responses"]],
  ["OpenRouter", ["openrouter", "openrouter-responses"]],
  ["Microsoft Azure", ["azure-openai", "azure-openai-responses", "azure-ai-foundry", "azure-foundry-claude"]],
  ["Amazon Bedrock", ["aws-bedrock", "aws-claude"]],
  ["Google Vertex AI", ["vertexai-claude"]],
  ["xAI", ["xai", "xai-responses"]],
  ["Cerebras", ["cerebras", "cerebras-openai"]],
  ["LiteLLM", ["litellm", "litellm-openai"]],
];
const names: Record<string,string> = { lmstudio:"LM Studio", "llama-cpp":"llama.cpp", "huggingface":"Hugging Face", "mistral":"Mistral", "vercel":"Vercel", "ibm":"IBM watsonx", "meta":"Meta Llama", "nvidia":"NVIDIA", "xiaomi":"Xiaomi" };
export function providerName(key:string, fallback?:string) {
  return families.find(([,ids])=>ids.includes(key))?.[0] || names[key] || fallback || key;
}
export function connectionMethod(entry:RecordData) {
  if(entry.id === "openai-chatgpt") return t("ChatGPT account");
  if(entry.id === "google-oauth") return t("Google Cloud account");
  if(entry.credential === "local_server") return t("Local server");
  if(entry.credential === "cloud_configuration") return t("Cloud credentials");
  return t("API key");
}
export function providerMethods(catalog:RecordData[], key:string) {
  const name=providerName(key,catalog.find(x=>x.id===key)?.name);
  return catalog.filter(x=>!(x.id==="openai-responses" && key!==x.id && catalog.some(p=>p.id==="openai")) && x.status==="ready" && providerName(x.id,x.name)===name);
}
export function ProviderPicker({catalog,selected,disabled,onSelect,profiles=[]}:{catalog:RecordData[];selected:string;disabled:boolean;onSelect:(id:string)=>void;profiles?:RecordData[]}) {
  const [query,setQuery]=useState("");
  const ready=catalog.filter(x=>x.status==="ready");
  const grouped=new Map<string,RecordData[]>();
  for(const item of ready) {
    const name=providerName(item.id,item.name);
    grouped.set(name,[...(grouped.get(name)||[]),item]);
  }
  const priority=["OpenAI","Claude","Gemini","Ollama","OpenRouter"];
  const results=[...grouped].sort(([a],[b])=>{
    const ai=priority.indexOf(a),bi=priority.indexOf(b);
    return (ai<0?99:ai)-(bi<0?99:bi) || a.localeCompare(b);
  }).filter(([name,entries])=>[name,...entries.map(x=>x.id),...entries.map(connectionMethod)].join(" ").toLowerCase().includes(query.trim().toLowerCase()));
  return <nav className="provider-directory" aria-label={t("Providers")}>
    <label className="provider-search"><Search size={16} aria-hidden="true"/><input type="search" aria-label={t("Search providers")} placeholder={t("Search providers")} value={query} onChange={e=>setQuery(e.target.value)}/>{query && <button aria-label={t("Clear search")} onClick={()=>setQuery("")}><X size={14}/></button>}</label>
    <div className="provider-results">
      {results.map(([name,entries])=>{
        const active=entries.some(x=>x.id===selected);
        const saved=profiles.some(p=>entries.some(x=>x.id===p.provider_key));
        const preferred=entries.find(x=>x.id==="openai-chatgpt") || entries[0];
        return <button key={name} className="provider-choice" aria-current={active?"true":undefined} disabled={disabled} onClick={()=>onSelect(preferred.id)}>
          <span><strong><bdi>{name}</bdi></strong><small>{saved?t("Account saved"):Array.from(new Set(entries.map(connectionMethod))).join(" · ")}</small></span>
          {saved?<Check size={15} aria-label={t("Account saved")}/>:<ChevronRight size={15} aria-hidden="true"/>}
        </button>;
      })}
      {!results.length && <p className="muted" role="status">{t("No matching providers. Try another name.")}</p>}
    </div>
  </nav>;
}
