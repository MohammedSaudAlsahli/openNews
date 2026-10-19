// @vitest-environment jsdom
import React from 'react';
import { beforeEach, afterEach, it, expect, vi } from 'vitest';
import { act, render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import { Articles } from './pages';
import { call } from './engine';
vi.mock('./engine', async original=>({...await original<typeof import('./engine')>(),call:vi.fn()}));
vi.mock('./article-explanation',()=>({ArticleExplanation:()=>null}));
const card={id:'news1',title:'Example news',url:'https://example.com/story',source_title:'Example',body_status:'excerpt',summary:'Preview text'};
beforeEach(()=>{vi.stubGlobal("localStorage",{getItem:()=>null,setItem:vi.fn()})});
afterEach(()=>{cleanup();vi.resetAllMocks();vi.unstubAllGlobals();vi.useRealTimers()});
function setup(article: Promise<any>) {
 vi.mocked(call).mockImplementation(async (command:string)=>{
  if(command==='news.list') return {articles:[card],has_more:false} as any;
  if(command==='news.summary.states') return {states:{}} as any;
  if(command==='news.article') return article;
  if(command==='news.related') return new Promise(()=>{});
  return {} as any;
 });
 render(<Articles snapshot={{}} onError={vi.fn()}/>);
}
it('opens the reader and report action before a slow local request resolves',async()=>{
 setup(new Promise(()=>{}));
 fireEvent.click(await screen.findByRole('button',{name:'Example news'}));
 expect(screen.getByRole('heading',{name:'Example news'})).toBeTruthy();
 expect(screen.getByRole('button',{name:'Report this article'})).toBeTruthy();
 expect(screen.getByText('Opening saved article…')).toBeTruthy();
});
it('renders cached full text without network recovery or waiting for related stories',async()=>{
 setup(Promise.resolve({...card,body_status:'full',text:'Cached article body'}));
 fireEvent.click(await screen.findByRole('button',{name:'Example news'}));
 await waitFor(()=>expect(screen.getByText('Cached article body')).toBeTruthy());
 expect(vi.mocked(call).mock.calls.some(([command])=>command==='news.reader')).toBe(false);
 expect(screen.queryByText('Retrieving article text…')).toBeNull();
});

it('refreshes the visible local list without asking publishers to sync',async()=>{
 vi.useFakeTimers();
 setup(new Promise(()=>{}));
 await act(async()=>{await vi.advanceTimersByTimeAsync(300)});
 await act(async()=>{ await vi.advanceTimersByTimeAsync(60000); });
 expect(vi.mocked(call).mock.calls.filter(([command])=>command==='news.list').length).toBeGreaterThan(1);
 expect(vi.mocked(call).mock.calls.some(([command])=>command==='news.sync')).toBe(false);
});
