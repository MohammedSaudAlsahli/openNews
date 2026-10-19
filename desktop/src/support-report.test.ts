import { describe, it, expect } from 'vitest';
import { issueUrl } from './support-report';
describe('GitHub report draft', () => {
  it('prefills the incident and diagnostics without submitting', () => {
    const url = new URL(issueUrl('openNews 0.3\noperation: feed.sync', 'UNEXPECTED_EXIT'));
    expect(url.pathname).toBe('/MohammedSaudAlsahli/openStudio/issues/new');
    expect(url.searchParams.get('body')).toContain('feed.sync');
    expect(url.searchParams.get('title')).toContain('UNEXPECTED_EXIT');
  });
  it('does not allow raw error content into the incident title', () => {
    expect(new URL(issueUrl('safe', 'token=secret')).searchParams.get('title')).toBe('[openNews] USER_REPORT');
  });
  it('bounds the diagnostic payload', () => {
    expect(new URL(issueUrl('x'.repeat(90000))).searchParams.get('body')!.length).toBeLessThan(5000);
  });
});
it('includes useful article context but strips URL secrets', () => {
 const url = new URL(issueUrl('safe','ARTICLE_READING_PROBLEM',{title:'Test article',url:'https://user:secret@example.com/story?token=secret#private',source:'Publisher',articleId:'a1',stage:'fetching_text',elapsedMs:5432,bodyStatus:'excerpt'}));
 const body=url.searchParams.get('body')!;
 expect(body).toContain('Test article');
 expect(body).toContain('https://example.com/story');
 expect(body).toContain('5432 ms');
 expect(body).not.toContain('secret');
 expect(body).not.toContain('private');
});
