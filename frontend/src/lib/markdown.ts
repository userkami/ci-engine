/**
 * Battlecard -> Markdown export (BUILD_GUIDE Phase 5).
 */
import type { BattlecardOutput } from "@/types";

const SWOT_KEYS: Array<["strengths" | "weaknesses" | "opportunities" | "threats", string]> = [
  ["strengths", "Strengths"],
  ["weaknesses", "Weaknesses"],
  ["opportunities", "Opportunities"],
  ["threats", "Threats"],
];

export function battlecardToMarkdown(
  card: BattlecardOutput,
  target?: string | null,
  competitor?: string | null,
): string {
  const lines: string[] = [];
  const title =
    target && competitor ? `${target} vs ${competitor}` : "Battlecard";
  lines.push(`# ${title}`, "");

  lines.push("## Executive Summary", "");
  lines.push(card.executive_summary, "");

  if (card.swot) {
    lines.push("## SWOT", "");
    for (const [key, label] of SWOT_KEYS) {
      const items = card.swot[key] ?? [];
      lines.push(`### ${label}`);
      if (items.length === 0) {
        lines.push("- _No evidence captured._");
      } else {
        items.forEach((item) => lines.push(`- ${item}`));
      }
      lines.push("");
    }
  }

  lines.push("## Pricing", "");
  if (card.pricing.length === 0) {
    lines.push("- _No pricing data found._");
  }
  for (const tier of card.pricing) {
    lines.push(`### ${tier.name} — ${tier.price}`);
    for (const limitation of tier.limitations) {
      lines.push(`- ⚠ ${limitation}`);
    }
    lines.push(`- Source: ${tier.source_url}`);
    lines.push("");
  }

  lines.push("## Churn Drivers & Rebuttals", "");
  if (card.churn_drivers.length === 0) {
    lines.push("- _No verified review quotes found._");
  }
  for (const driver of card.churn_drivers) {
    lines.push(`### ${driver.pain_point}`);
    lines.push("");
    lines.push(`> "${driver.exact_quote}"`);
    lines.push("");
    lines.push(`— ${driver.source_platform} · ${driver.source_url}`);
    lines.push("");
    lines.push(`**Rebuttal:** ${driver.objection_rebuttal}`);
    lines.push("");
  }

  lines.push("## Landmine Questions", "");
  if (card.landmine_questions.length === 0) {
    lines.push("- _None captured._");
  }
  card.landmine_questions.forEach((q) => lines.push(`- ${q}`));
  lines.push("");

  return lines.join("\n");
}

export function downloadMarkdown(content: string, filename: string): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}