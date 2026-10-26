// @vitest-environment jsdom
import React from "react";
import {afterEach,it,expect,vi} from "vitest";
import {cleanup,render,screen,fireEvent} from "@testing-library/react";
import {ProviderPicker} from "./provider-picker";
import {Connections} from "./connections";
import {call} from "./engine";
import {invoke} from "@tauri-apps/api/core";
vi.mock("./engine",()=>({call:vi.fn()}));
vi.mock("@tauri-apps/api/core",()=>({invoke:vi.fn()}));
afterEach(()=>{cleanup();vi.resetAllMocks();});
const providers=[
 {id:"openai",name:"OpenAIResponses",status:"ready",credential:"api_key"},
 {id:"openai-chatgpt",name:"ChatGPT",status:"ready",credential:"oauth"},
 {id:"openai-responses",name:"OpenAIResponses",status:"ready",credential:"api_key"},
 {id:"google",name:"Gemini",status:"ready",credential:"api_key"},
 {id:"google-oauth",name:"Gemini",status:"ready",credential:"oauth"},
];
it("groups adapters under a recognizable provider, prefers account sign-in and supports search",()=>{
 const select=vi.fn();render(<ProviderPicker catalog={providers} selected="openai-chatgpt" disabled={false} onSelect={select}/>);
 expect(screen.getAllByRole("button",{name:/OpenAI/})).toHaveLength(1);
 fireEvent.click(screen.getByRole("button",{name:/OpenAI/}));expect(select).toHaveBeenCalledWith("openai-chatgpt");
 fireEvent.change(screen.getByRole("searchbox"),{target:{value:"missing-provider"}});
 expect(screen.getByRole("status").textContent).toContain("No matching providers");
 fireEvent.click(screen.getByRole("button",{name:"Clear search"}));expect(screen.getByRole("button",{name:/Gemini/})).toBeTruthy();
});
it("makes ChatGPT sign-in visible without finding an adapter and opens the returned URL",async()=>{
 vi.mocked(call).mockImplementation(async command=>command==="providers.catalog"?{providers}:command==="providers.auth.start"?{auth_id:"attempt",authorization_url:"https://auth.openai.com/test"}:{status:"waiting"});
 render(<Connections snapshot={{profiles:[]}} refresh={async()=>{}} onError={vi.fn()}/>);
 fireEvent.click(await screen.findByRole("button",{name:"Sign in with ChatGPT"}));
 await screen.findByText("Complete sign-in in your browser.");
 expect(call).toHaveBeenCalledWith("providers.auth.start",expect.objectContaining({provider_key:"openai-chatgpt"}));
 expect(invoke).toHaveBeenCalledWith("open_external",{address:"https://auth.openai.com/test"});
});
it("explains Google project setup and does not start OAuth with missing registration",async()=>{
 vi.mocked(call).mockResolvedValue({providers});
 render(<Connections snapshot={{profiles:[]}} refresh={async()=>{}} onError={vi.fn()}/>);
 fireEvent.click(await screen.findByRole("button",{name:/Gemini/}));
 fireEvent.change(screen.getByRole("combobox",{name:"Connection method"}),{target:{value:"google-oauth"}});
 expect((screen.getByRole("button",{name:"Sign in with Google"}) as HTMLButtonElement).disabled).toBe(true);
 expect(screen.getByText(/Cloud billing applies/)).toBeTruthy();
 expect(screen.getByLabelText("OAuth client secret").getAttribute("type")).toBe("password");
 expect(vi.mocked(call).mock.calls.some(([name])=>name==="providers.auth.start")).toBe(false);
});
