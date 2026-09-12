"use client";
import { Check, Loader, Save, Settings, TriangleAlert } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { ApiKeysPanel, CEntry, CState, ModelPanel } from "./panels";

const TK = "ci_admin_token";

function AdminPage() {
  const [token, setToken] = useState("");
  const [config, setConfig] = useState<CState | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ t: "ok" | "err"; s: string } | null>(null);
  const [tk, setTk] = useState<string | null>(null);
  const [tr, setTr] = useState<Record<string,{ok:boolean;text:string}>>({});
  const [sk, setSk] = useState<Record<string,boolean>>({});
  const [tiVal, setTiVal] = useState("");

  useEffect(() => { const s = localStorage.getItem(TK); if (s) setToken(s); }, []);
  const doFetch = useCallback(async () => {
    if (!token) return;
    setLoading(true); setMsg(null);
    try {
      const r = await fetch("/api/actions/admin", { headers: { "x-admin-token": token } });
      const b = await r.json();
      if (!r.ok || !b.config) { setMsg({ t: "err", s: b.error ?? `Failed (${r.status})` }); return; }
      setConfig(b.config);
      const d: Record<string,string> = {};
      for (const [k,e] of Object.entries(b.config)) d[k] = (e as CEntry).value;
      setDrafts(d);
    } catch (e) { setMsg({ t: "err", s: e instanceof Error ? e.message : "error" }); }
    finally { setLoading(false); }
  }, [token]);
  useEffect(() => { if (token) doFetch(); else setConfig(null); }, [token, doFetch]);

  const upd = (k: string, v: string) => setDrafts(p => ({ ...p, [k]: v }));
  const changed = config && Object.entries(drafts).some(([k,v]) => v !== (config as unknown as Record<string,CEntry>)[k]?.value);

  async function save() {
    if (!token || !config) return;
    setSaving(true); setMsg(null);
    const u: Record<string,string> = {};
    for (const [k,v] of Object.entries(drafts)) if (v !== config[k as keyof CState]?.value) u[k] = v;
    try {
      const r = await fetch("/api/actions/admin", {
        method: "PUT", headers: { "Content-Type":"application/json", "x-admin-token":token }, body: JSON.stringify({ updates: u }),
      });
      const b = await r.json();
      if (!r.ok) { setMsg({ t: "err", s: b.error ?? b.detail ?? `Failed (${r.status})` }); return; }
      setMsg({ t: "ok", s: "Saved. Changes take effect immediately." });
      await doFetch();
    } catch (e) { setMsg({ t: "err", s: e instanceof Error ? e.message : "error" }); }
    finally { setSaving(false); }
  }

  async function test(key: string, spec: string) {
    if (!token || !spec.trim()) return;
    setTk(key);
    try {
      const heavy = key === "LLM_HEAVY_MODEL";
      const r = await fetch("/api/actions/admin", {
        method: "POST", headers: { "Content-Type":"application/json", "x-admin-token":token },
        body: JSON.stringify({ role: heavy ? "heavy" : "fast", model_spec: spec }),
      });
      const b = await r.json();
      setTr(p => ({ ...p, [key]: { ok: !!b.ok, text: b.message ?? b.error ?? "" } }));
    } catch (e) { setTr(p => ({ ...p, [key]: { ok: false, text: e instanceof Error ? e.message : "error" } })); }
    finally { setTk(null); }
  }

  function saveToken() {
    const v = tiVal.trim(); setToken(v);
    v ? localStorage.setItem(TK, v) : localStorage.removeItem(TK);
  }

  if (!token) {
    return (
      <div className="mx-auto max-w-md p-6">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Settings className="h-5 w-5" /> Admin Access</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">Enter your admin token to manage configuration.</p>
            <div className="flex gap-2">
              <Input type="password" placeholder="Admin token" value={tiVal} onChange={e => setTiVal(e.target.value)} onKeyDown={e => { if (e.key==="Enter") saveToken(); }} />
              <Button onClick={saveToken}>Unlock</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="flex items-center gap-2 text-2xl font-bold"><Settings className="h-6 w-6" /> Admin Configuration</h1>
      {msg && (
        <div role="alert" className={cn("flex items-start gap-2 rounded-lg border p-3 text-sm", msg.t==="ok" ? "border-green-500/40 bg-green-500/10 text-green-600" : "border-destructive/40 bg-destructive/10 text-destructive")}>
          {msg.t==="ok" ? <Check className="mt-0.5 h-4 w-4 shrink-0" /> : <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />}
          <span>{msg.s}</span>
        </div>
      )}
      {loading && !config ? (
        <div className="flex items-center gap-2 p-6 text-muted-foreground"><Loader className="h-4 w-4 animate-spin" /> Loading...</div>
      ) : config ? (
        <>
          <ModelPanel config={config} drafts={drafts} tr={tr} tk={tk} upd={upd} test={test} />
          <ApiKeysPanel config={config} drafts={drafts} tr={tr} tk={tk} sk={sk} upd={upd} test={test} setSk={setSk} />
          <div className="flex items-center gap-3">
            <Button disabled={!changed || saving} onClick={save} className="min-w-[120px]">
              {saving ? <Loader className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {saving ? "Saving..." : "Save Changes"}
            </Button>
            <Button variant="outline" onClick={doFetch}>Refresh</Button>
            {!changed && <span className="text-sm text-muted-foreground">Changes take effect immediately.</span>}
          </div>
        </>
      ) : null}
    </div>
  );
}

export default AdminPage;
