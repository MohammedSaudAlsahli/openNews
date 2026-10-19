// @vitest-environment jsdom
import React from 'react';
import { it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { RefreshInterval } from './refresh-interval';
import { call } from './engine';
vi.mock('./engine',()=>({call:vi.fn().mockResolvedValue({})}));
afterEach(()=>{cleanup();vi.clearAllMocks()});
it('saves a preset immediately with human-readable hour labels',async()=>{
 const saved=vi.fn().mockResolvedValue(undefined);
 render(<RefreshInterval id="source" title="Source" minutes={5} onSaved={saved} onError={vi.fn()}/>);
 expect(screen.getByRole('option',{name:'1 hour'})).toBeTruthy();
 expect(screen.queryByRole('spinbutton')).toBeNull();
 fireEvent.change(screen.getByRole('combobox'),{target:{value:'1'}});
 await waitFor(()=>expect(saved).toHaveBeenCalled());
 expect(call).toHaveBeenCalledWith('news.update',{subscription_id:'source',interval_minutes:1});
});
it('restores the previous selection if saving fails',async()=>{
 vi.mocked(call).mockRejectedValueOnce(new Error('offline'));
 const error=vi.fn();
 render(<RefreshInterval id="source" title="Source" minutes={7} onSaved={vi.fn()} onError={error}/>);
 expect((screen.getByRole('combobox') as HTMLSelectElement).value).toBe('7');
 fireEvent.change(screen.getByRole('combobox'),{target:{value:'30'}});
 await waitFor(()=>expect(error).toHaveBeenCalled());
 expect((screen.getByRole('combobox') as HTMLSelectElement).value).toBe('7');
});
