import { getLocale } from './locale';
export function relativeTime(value: string | undefined, locale: string, now = Date.now()) {
  const timestamp = value ? Date.parse(value) : NaN;
  if (!Number.isFinite(timestamp)) return locale === 'ar' ? 'تاريخ النشر غير متوفر' : 'Publication date unavailable';
  const seconds = (timestamp - now) / 1000;
  if (Math.abs(seconds) < 60) return locale === 'ar' ? 'الآن' : 'Just now';
  const units = [[31536000,'year'],[2592000,'month'],[86400,'day'],[3600,'hour'],[60,'minute']] as const;
  const [size, unit] = units.find(([size]) => Math.abs(seconds) >= size)!;
  return new Intl.RelativeTimeFormat(locale, {numeric:'always'}).format(Math.trunc(seconds / size),unit);
}
export function RelativeTime({value, now}:{value?:string;now:number}) {
  const locale=getLocale();
  const valid=Boolean(value && Number.isFinite(Date.parse(value)));
  return <time dateTime={valid ? value : undefined} title={valid ? new Date(value!).toLocaleString(locale) : undefined}>{relativeTime(value,locale,now)}</time>;
}
