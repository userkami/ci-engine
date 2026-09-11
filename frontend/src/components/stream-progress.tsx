"use client";

import { Check, Loader, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { sseStreamUrl } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  AGENT_STEP_ORDER,
  STEP_LABELS,
  type AgentStep,
  type ProgressEventPayload,
} from "@/types";
import { Badge } from "@/components/ui/badge";
import { ProgressIndicator, ProgressRoot } from "@/components/ui/progress";

export interface StreamResult {
  step: "completed" | "failed";
  message: string;
  data?: unknown;
}

interface StepState {
  name: AgentStep | string;
  state: "done" | "active" | "todo" | "error";
}

/**
 * Real-Time Agent Streamer: subscribes to the FastAPI SSE endpoint with a
 * native EventSource and renders the live multi-step progress bar.
 */
export function StreamProgress({
  jobId,
  onTerminal,
}: {
  jobId: string;
  onTerminal?: (result: StreamResult) => void;
}) {
  const [message, setMessage] = useState("Job queued on the research worker…");
  const [activeIndex, setActiveIndex] = useState(-1);
  const [connectionState, setConnectionState] = useState<
    "connecting" | "live" | "error"
  >("connecting");
  const [terminal, setTerminal] = useState(false);

  useEffect(() => {
    let lastStep = "";
    const source = new EventSource(sseStreamUrl(jobId));

    source.onopen = () => setConnectionState("live");
    source.onerror = () => {
      setConnectionState("error");
    };
    source.onmessage = (rawEvent) => {
      const event = rawEvent as MessageEvent;
      let payload: ProgressEventPayload | null = null;
      try {
        payload = JSON.parse(event.data) as ProgressEventPayload;
      } catch {
        return;
      }
      if (!payload || typeof payload.step !== "string") return;

      if (typeof payload.message === "string" && payload.message) {
        setMessage(payload.message);
      }
      setConnectionState("live");

      if (AGENT_STEP_ORDER.includes(payload.step as AgentStep)) {
        lastStep = payload.step;
        const idx = AGENT_STEP_ORDER.indexOf(payload.step as AgentStep);
        setActiveIndex(idx);
        return;
      }

      if (payload.step === "completed" || payload.step === "failed") {
        setActiveIndex(AGENT_STEP_ORDER.length);
        setTerminal(true);
        setMessage(payload.message ?? "Finished");
        source.close();
        onTerminal?.({
          step: payload.step,
          message: payload.message ?? "",
          data: payload.data,
        });
      }
    };

    return () => source.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const stepState = (index: number): StepState => {
    if (terminal && activeIndex === AGENT_STEP_ORDER.length) {
      return { name: AGENT_STEP_ORDER[index], state: "done" };
    }
    if (index < activeIndex) {
      return { name: AGENT_STEP_ORDER[index], state: "done" };
    }
    if (index === activeIndex) {
      return { name: AGENT_STEP_ORDER[index], state: "active" };
    }
    return { name: AGENT_STEP_ORDER[index], state: "todo" };
  };

  const progressValue =
    terminal && activeIndex === AGENT_STEP_ORDER.length
      ? 100
      : Math.max(0, (activeIndex * 100) / AGENT_STEP_ORDER.length);

  return (
    <div className="rounded-xl border bg-card p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <Loader className="h-4 w-4 animate-spin text-primary" />
        <h3 className="text-sm font-semibold">Agent working in real time</h3>
        <Badge
          variant={connectionState === "error" ? "destructive" : "secondary"}
          className="ml-auto"
        >
          {connectionState === "live"
            ? "live"
            : connectionState === "error"
              ? "reconnecting…"
              : "connecting…"}
        </Badge>
      </div>

      <div className="mt-4 flex items-center gap-2">
        {AGENT_STEP_ORDER.map((step, index) => {
          const state = stepState(index).state;
          return (
            <div
              key={step}
              className={cn(
                "flex flex-1 flex-col items-center gap-1",
                index < AGENT_STEP_ORDER.length - 1 ? "" : "",
              )}
            >
              <span
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-colors",
                  state === "done" && "bg-primary text-primary-foreground",
                  state === "active" && "border-2 border-primary text-primary",
                  state === "todo" && "bg-muted text-muted-foreground",
                )}
              >
                {state === "done" ? (
                  <Check className="h-4 w-4" />
                ) : (
                  index + 1
                )}
              </span>
              <span
                className={cn(
                  "text-xs font-medium",
                  state === "active" && "text-primary",
                  state === "todo" && "text-muted-foreground",
                )}
              >
                {STEP_LABELS[step as AgentStep]}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-4">
        <ProgressRoot value={progressValue}>
          <ProgressIndicator />
        </ProgressRoot>
      </div>

      <p className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
        {connectionState === "error" ? (
          <TriangleAlert className="h-4 w-4 shrink-0 text-amber-500" />
        ) : (
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
        )}
        <span className="truncate">{message}</span>
      </p>
    </div>
  );
}