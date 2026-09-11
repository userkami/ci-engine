"use client";

import { FileDown, Printer, TriangleAlert } from "lucide-react";

import { battlecardToMarkdown, downloadMarkdown } from "@/lib/markdown";
import { cn } from "@/lib/utils";
import type {
  BattlecardOutput,
  ChurnDriver,
  PricingTier,
  SWOTAnalysis,
} from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  TabsContent,
  TabsList,
  TabsRoot,
  TabsTrigger,
} from "@/components/ui/tabs";

function SummaryPanel({ card }: { card: BattlecardOutput }) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border p-4">
        <h4 className="text-sm font-semibold text-muted-foreground">
          Executive summary
        </h4>
        <p className="mt-2 text-sm leading-relaxed">{card.executive_summary}</p>
      </div>
      {card.swot && <SwotGrid swot={card.swot} />}
    </div>
  );
}

const SWOT_LABELS: Array<[keyof SWOTAnalysis, string, string]> = [
  ["strengths", "Strengths", "text-emerald-600"],
  ["weaknesses", "Weaknesses", "text-destructive"],
  ["opportunities", "Opportunities", "text-sky-600"],
  ["threats", "Threats", "text-amber-600"],
];

function SwotGrid({ swot }: { swot: SWOTAnalysis }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {SWOT_LABELS.map(([key, label, color]) => (
        <div key={label} className="rounded-lg border p-4">
          <h4 className={cn("text-sm font-semibold", color)}>{label}</h4>
          <ul className="mt-2 space-y-1 pl-4 text-sm">
            {(swot[key] ?? []).map((item, i) => (
              <li key={i}>• {item}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function PricingPanel({ pricing }: { pricing: PricingTier[] }) {
  if (pricing.length === 0) {
    return <EmptyNote text="No pricing data was found in the research corpus." />;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b bg-muted/40 text-muted-foreground">
            <th className="px-3 py-2.5">Tier</th>
            <th className="px-3 py-2.5">Price</th>
            <th className="px-3 py-2.5">Limitations &amp; hidden costs</th>
            <th className="px-3 py-2.5">Source</th>
          </tr>
        </thead>
        <tbody>
          {pricing.map((tier) => (
            <tr key={tier.name} className="border-b">
              <td className="px-3 py-3 font-medium">{tier.name}</td>
              <td className="px-3 py-3 tabular-nums">{tier.price}</td>
              <td className="px-3 py-3">
                <ul className="space-y-1">
                  {tier.limitations.map((limitation, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-1.5 text-muted-foreground"
                    >
                      <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                      <span>{limitation}</span>
                    </li>
                  ))}
                </ul>
              </td>
              <td className="px-3 py-3">
                <a
                  href={tier.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary hover:underline"
                >
                  source
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChurnGrid({ drivers }: { drivers: ChurnDriver[] }) {
  if (drivers.length === 0) {
    return <EmptyNote text="No verified customer quotes were found." />;
  }
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {drivers.map((driver, i) => (
        <Card key={i} className="py-0">
          <CardContent className="space-y-2.5 py-4">
            <div className="flex items-center gap-2">
              <Badge variant="outline">{driver.source_platform}</Badge>
              <a
                href={driver.source_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-muted-foreground hover:underline"
              >
                source review ↗
              </a>
            </div>
            <h4 className="font-medium">{driver.pain_point}</h4>
            <blockquote className="border-l-2 border-muted pl-3 text-sm italic leading-relaxed text-muted-foreground">
              “{driver.exact_quote}”
            </blockquote>
            <div className="rounded-lg bg-accent/50 p-3">
              <p className="text-xs font-semibold text-accent-foreground">
                Rebuttal talk track
              </p>
              <p className="mt-1 text-sm leading-relaxed">
                {driver.objection_rebuttal}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function LandminesPanel({ questions }: { questions: string[] }) {
  if (questions.length === 0) {
    return <EmptyNote text="No landmine questions were captured." />;
  }
  return (
    <ol className="list-decimal space-y-2.5 pl-5">
      {questions.map((q, i) => (
        <li key={i} className="text-sm leading-relaxed">
          {q}
        </li>
      ))}
    </ol>
  );
}

function EmptyNote({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
      {text}
    </div>
  );
}

export interface BattlecardViewProps {
  card: BattlecardOutput;
  target?: string | null;
  competitor?: string | null;
  demo?: boolean;
}

/**
 * Battlecard Presentation View: tabbed report canvas with Markdown export
 * and a print-friendly stylesheet (globals.css @media print).
 */
export function BattlecardView({
  card,
  target,
  competitor,
  demo = false,
}: BattlecardViewProps) {
  const filename = `${
    competitor?.toLowerCase().replace(/\s+/g, "-") ?? "battlecard"
  }-battlecard.md`;

  return (
    <Card className="print:shadow-none">
      <CardHeader className="print:hidden">
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle>
            {competitor ? `${competitor} battlecard` : "Battlecard"}
            {target ? (
              <span className="text-muted-foreground"> · vs {target}</span>
            ) : null}
          </CardTitle>
          {demo ? <Badge variant="secondary">sample preview</Badge> : null}
        </div>
        <CardDescription>
          Citation-backed pricing teardown, verified churn drivers and
          rebuttal talk tracks.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap items-center gap-2 print:hidden">
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              downloadMarkdown(
                battlecardToMarkdown(card, target, competitor),
                filename,
              )
            }
          >
            <FileDown className="h-4 w-4" />
            Export to Markdown
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => window.print()}
          >
            <Printer className="h-4 w-4" />
            Print / PDF
          </Button>
        </div>

        <TabsRoot className="mt-3" defaultValue="summary">
          <TabsList className="print:hidden">
            <TabsTrigger value="summary">Summary &amp; SWOT</TabsTrigger>
            <TabsTrigger value="pricing">Pricing</TabsTrigger>
            <TabsTrigger value="churn">Churn drivers</TabsTrigger>
            <TabsTrigger value="landmines">Landmines</TabsTrigger>
          </TabsList>
          <TabsContent value="summary">
            <SummaryPanel card={card} />
          </TabsContent>
          <TabsContent value="pricing">
            <PricingPanel pricing={card.pricing} />
          </TabsContent>
          <TabsContent value="churn">
            <ChurnGrid drivers={card.churn_drivers} />
          </TabsContent>
          <TabsContent value="landmines">
            <LandminesPanel questions={card.landmine_questions} />
          </TabsContent>
        </TabsRoot>
      </CardContent>
    </Card>
  );
}