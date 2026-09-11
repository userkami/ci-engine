"use client";

import { ArrowRight, Loader, Search, TriangleAlert } from "lucide-react";
import { useState } from "react";

import { actionUrl } from "@/lib/api";
import type { BattlecardRecord } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { StreamProgress, type StreamResult } from "./stream-progress";
import { BattlecardView } from "./battlecard-view";

type Phase = "idle" | "submitting" | "running" | "done" | "error";

/**
 * Research Input Bar + real-time stream + battlecard transition. Client
 * component because it owns state + streaming; every backend mutation
 * flows through the /api/actions server routes.
 */
export function ResearchRunner() {
  const [target, setTarget] = useState("");
  const [competitor, setCompetitor] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [battlecard, setBattlecard] = useState<BattlecardRecord | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const busy = phase === "submitting" || phase === "running";

  async function startResearch() {
    const formattedTarget = target.trim();
    const formattedCompetitor = competitor.trim();
    if (!formattedTarget || !formattedCompetitor) {
      setErrorMsg("Enter both your company and the competitor to analyze.");
      return;
    }
    setErrorMsg(null);
    setPhase("submitting");
    setBattlecard(null);
    try {
      const res = await fetch(actionUrl("jobs"), {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_company: formattedTarget,
          competitor: formattedCompetitor,
        }),
      });
      const body = (await res.json()) as { job_id?: string; error?: string };
      if (!res.ok || !body.job_id) {
        setErrorMsg(body.error ?? "Could not start the research job.");
        setPhase("error");
        return;
      }
      setJobId(body.job_id);
      setPhase("running");
    } catch {
      setErrorMsg("Network error while starting the research job.");
      setPhase("error");
    }
  }

  async function handleTerminal(result: StreamResult) {
    if (result.step === "completed") {
      const battlecardId = (result.data as { battlecard_id?: string } | null)
        ?.battlecard_id;
      if (!battlecardId) {
        setErrorMsg("The job finished but no report id was returned.");
        setPhase("error");
        return;
      }
      try {
        const res = await fetch(actionUrl(`battlecards/${battlecardId}`), {
          cache: "no-store",
        });
        const body = await res.json();
        if (res.ok && body && body.report_data) {
          setBattlecard(body as BattlecardRecord);
          setPhase("done");
          return;
        }
        throw new Error(body.error ?? "Could not load the report");
      } catch (err) {
        setErrorMsg(
          err instanceof Error ? err.message : "Could not load the report.",
        );
        setPhase("error");
        return;
      }
    }
    setErrorMsg(
      result.message
        ? `Research failed: ${result.message}`
        : "Research failed. Please try again.",
    );
    setPhase("error");
  }
return (
    <Card className="print:hidden">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-4 w-4 text-primary" />
          New competitive analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex flex-col gap-1 text-sm text-muted-foreground">
            Your company
            <Input
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="e.g. Linear"
              disabled={busy}
              aria-label="Your company"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-muted-foreground">
            Competitor name
            <Input
              value={competitor}
              onChange={(e) => setCompetitor(e.target.value)}
              placeholder="e.g. Jira"
              disabled={busy}
              aria-label="Competitor name"
            />
          </label>
          <Button
            variant="default"
            size="lg"
            disabled={busy || !target.trim() || !competitor.trim()}
            onClick={startResearch}
          >
            {phase === "submitting" ? (
              <>
                <Loader className="h-4 w-4 animate-spin" />
                Starting…
              </>
            ) : (
              <>
                Analyze
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>

        {errorMsg && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
          >
            <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {phase === "running" && jobId && (
          <StreamProgress jobId={jobId} onTerminal={handleTerminal} />
        )}

        {(phase === "idle" || phase === "error") && (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            Each analysis spends 5 credits and typically takes 1–3 minutes.
          </p>
        )}

        {phase === "done" && battlecard && (
          <BattlecardView
            card={battlecard.report_data}
            target={battlecard.target_company}
            competitor={battlecard.competitor}
          />
        )}
      </CardContent>
    </Card>
  );
}