"use client";
import { Check, Loader } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export interface CEntry { value: string; source: string; }
export interface CState {
  LLM_FAST_MODEL: CEntry; LLM_HEAVY_MODEL: CEntry;
  OPENROUTER_API_KEY: CEntry; TAVILY_API_KEY: CEntry; FIRECRAWL_API_KEY: CEntry;
}
export const LB: Record<string,string> = {
  LLM_FAST_MODEL: "Fast Model", LLM_HEAVY_MODEL: "Heavy Model",
  OPENROUTER_API_KEY: "OpenRouter Key", TAVILY_API_KEY: "Tavily Key", FIRECRAWL_API_KEY: "Firecrawl Key",
};
export const HG: Record<string,string> = {
  LLM_FAST_MODEL: "e.g. openrouter:anthropic/claude-3.5-haiku",
  LLM_HEAVY_MODEL: "e.g. openrouter:anthropic/claude-3.5-sonnet",
  OPENROUTER_API_KEY: "Get key at openrouter.ai/keys",
  TAVILY_API_KEY: "Get key at app.tavily.com",
  FIRECRAWL_API_KEY: "Get key at firecrawl.dev",
};
const SUG = [
  "openrouter:anthropic/claude-3.5-sonnet", "openrouter:anthropic/claude-3.5-haiku",
  "openrouter:openai/gpt-4o", "openrouter:openai/gpt-4o-mini",
  "openrouter:google/gemini-2.0-flash-001", "openrouter:meta-llama/llama-3.1-405b-instruct",
];

export function ModelPanel({ config, drafts, tr, tk, upd, test }: {
  config: CState; drafts: Record<string,string>;
  tr: Record<string,{ok:boolean;text:string}>; tk: string|null;
  upd: (k:string,v:string)=>void; test: (k:string,s:string)=>Promise<void>;
}) {
  return (
    <Card>
      <CardHeader><CardTitle>LLM Models</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {(["LLM_FAST_MODEL","LLM_HEAVY_MODEL"] as const).map(key => (
          <div key={key} className="space-y-2">
            <label className="text-sm font-medium">{LB[key]}</label>
            <Input list={`sg-${key}`} value={drafts[key]??""} onChange={e => upd(key, e.target.value)} placeholder="provider:model_name" />
            <datalist id={`sg-${key}`}>
              {SUG.map(s => <option key={s} value={s} />)}
              <option value="google_genai:gemini-2.5-flash" />
              <option value="anthropic:claude-3-5-sonnet-20241022" />
              <option value="openai:gpt-4o" />
            </datalist>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={!drafts[key]?.trim() || tk===key} onClick={() => test(key, drafts[key])}>
                {tk===key ? <Loader className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />} Test
              </Button>
              {tr[key] && <span className={cn("text-xs", tr[key].ok ? "text-green-500" : "text-destructive")}>{tr[key].text}</span>}
              <span className="ml-auto text-xs text-muted-foreground">Source: {config[key].source}</span>
            </div>
            <p className="text-xs text-muted-foreground">{HG[key]}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function ApiKeysPanel({ config, drafts, tr, tk, sk, upd, test, setSk }: {
  config: CState; drafts: Record<string,string>;
  tr: Record<string,{ok:boolean;text:string}>; tk: string|null;
  sk: Record<string,boolean>; upd: (k:string,v:string)=>void; test: (k:string,s:string)=>Promise<void>;
  setSk: React.Dispatch<React.SetStateAction<Record<string,boolean>>>;
}) {
  return (
    <Card>
      <CardHeader><CardTitle>API Keys</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {(["OPENROUTER_API_KEY","TAVILY_API_KEY","FIRECRAWL_API_KEY"] as const).map(key => (
          <div key={key} className="space-y-2">
            <label className="text-sm font-medium">{LB[key]}</label>
            <div className="flex gap-2">
              <Input type={sk[key] ? "text" : "password"} value={drafts[key]??""} onChange={e => upd(key, e.target.value)} placeholder={LB[key]} className="font-mono text-sm" />
              <Button variant="outline" size="sm" onClick={() => setSk(p => ({ ...p, [key]: !p[key] }))}>{sk[key] ? "Hide" : "Show"}</Button>
            </div>
            <div className="flex items-center gap-2">
              {key==="OPENROUTER_API_KEY" && (
                <Button variant="outline" size="sm" disabled={!drafts[key]?.trim() || tk===key || !drafts["LLM_FAST_MODEL"]?.startsWith("openrouter:")} onClick={() => test(key, drafts["LLM_FAST_MODEL"]??"")}>
                  {tk===key ? <Loader className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />} Test
                </Button>
              )}
              {tr[key] && <span className={cn("text-xs", tr[key].ok ? "text-green-500" : "text-destructive")}>{tr[key].text}</span>}
              <span className="ml-auto text-xs text-muted-foreground">
                {config[key].value ? `Set (${config[key].source})` : "Not set"}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">{HG[key]}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
