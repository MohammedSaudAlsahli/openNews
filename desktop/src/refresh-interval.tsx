import { useEffect, useState } from 'react';
import { call } from './engine';
import { t, getLocale } from './locale';
const intervals = [1, 5, 15, 30, 60, 180, 360, 720, 1440];
function intervalLabel(minutes: number) {
 const hours = minutes >= 60 && minutes % 60 === 0;
 const days = minutes >= 1440 && minutes % 1440 === 0;
 return new Intl.NumberFormat(getLocale(), {style:'unit', unit:days?'day':hours?'hour':'minute', unitDisplay:'long'}).format(days?minutes/1440:hours?minutes/60:minutes);
}
export function RefreshInterval({id,title,minutes=5,onSaved,onError}:{id:string;title:string;minutes?:number;onSaved:()=>Promise<void>;onError:(message:string)=>void}) {
 const [value,setValue]=useState(minutes),[saving,setSaving]=useState(false);
 useEffect(()=>setValue(minutes),[minutes]);
 // Preserve a previously saved custom duration until the user chooses a preset.
 const options=intervals.includes(value)?intervals:[...intervals,value].sort((a,b)=>a-b);
 return <label className="refresh-interval">{t('Refresh interval')}
  <select value={value} disabled={saving} aria-busy={saving} aria-label={t('Refresh interval')+' '+title} onChange={async e=>{
   const next=Number(e.target.value), previous=value;
   if(saving || next===previous || !options.includes(next))return;
   setValue(next);setSaving(true);
   try {await call('news.update',{subscription_id:id,interval_minutes:next});}
   catch(error){setValue(previous);onError(String(error));setSaving(false);return;}
   try {await onSaved();}catch(error){onError(String(error));}finally{setSaving(false);}
  }}>
   {options.map(n=><option key={n} value={n}>{intervalLabel(n)}</option>)}
  </select>
 </label>;
}
