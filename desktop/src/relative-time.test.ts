// @vitest-environment jsdom
import { expect, it } from 'vitest';
import { relativeTime } from './relative-time';
const now=Date.parse('2026-10-19T10:00:00Z');
it('shows minutes, hours, days and months since publication',()=>{
 expect(relativeTime('2026-10-19T09:42:00Z','en',now)).toBe('18 minutes ago');
 expect(relativeTime('2026-10-19T09:00:00Z','en',now)).toBe('1 hour ago');
 expect(relativeTime('2026-10-18T10:00:00Z','en',now)).toBe('1 day ago');
 expect(relativeTime('2026-06-19T10:00:00Z','en',now)).toBe('4 months ago');
});
it('handles missing, invalid, future and Arabic dates truthfully',()=>{
 expect(relativeTime(undefined,'en',now)).toBe('Publication date unavailable');
 expect(relativeTime('bad','ar',now)).toBe('تاريخ النشر غير متوفر');
 expect(relativeTime('2026-10-19T11:00:00Z','en',now)).toBe('in 1 hour');
 expect(relativeTime('2026-10-19T09:59:40Z','ar',now)).toBe('الآن');
 expect(relativeTime('2026-10-19T09:42:00Z','ar',now)).toContain('قبل');
});
