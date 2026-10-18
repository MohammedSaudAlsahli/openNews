// @vitest-environment jsdom
import React from 'react';
import {afterEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {Trace,Markdown} from './components';
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}));
afterEach(cleanup);
describe('live public activity',()=>{
 it('updates while working, collapses after completion, and can be reopened',()=>{
  const first={execution:{reasoning_summary:'أبحث في الأخبار',steps:[]}};
  const {rerender}=render(<Trace running data={first}/>);
  expect(screen.getByText('أبحث في الأخبار')).toBeTruthy();
  const next={execution:{reasoning_summary:'أقارن المصادر الآن',steps:[{id:'1',kind:'reading',detail:'مصدر الخبر'}]}};
  rerender(<Trace running data={next}/>);
  expect(screen.queryByText('أبحث في الأخبار')).toBeNull();
  expect(screen.getByText('أقارن المصادر الآن')).toBeTruthy();
  expect(screen.getByText('مصدر الخبر')).toBeTruthy();
  rerender(<Trace data={next}/>);
  expect(screen.queryByText('أقارن المصادر الآن')).toBeNull();
  fireEvent.click(screen.getByRole('button'));
  expect(screen.getByText('أقارن المصادر الآن')).toBeTruthy();
 });
 it('does not fall back to the wrong language when translation is pending',()=>{
  render(<Trace running data={{execution:{summary_language:'ar',reasoning_summary:'',reasoning_summaries:{en:'English only'},summary_translation_state:'pending'}}}/>);
  expect(screen.queryByText('English only')).toBeNull();
 });
 it('renders Arabic markdown in RTL and keeps embedded HTML inert',()=>{
  const {container}=render(<Markdown text={'## تعليمات\n\n<script>alert(1)</script>'}/>);
  expect(container.querySelector('.prose')?.getAttribute('dir')).toBe('rtl');
  expect(container.querySelector('script')).toBeNull();
  expect(screen.getByRole('heading').textContent).toBe('تعليمات');
 });
});

import {articleExcerpt} from './engine';
it('does not fill article cards with aggregator navigation links',()=>{
 expect(articleExcerpt('Article URL: [https://example.com](https://example.com) Comments URL: ...')).toBe('');
 expect(articleExcerpt('A useful [story](https://example.com) about science.')).toBe('A useful story about science.');
});
