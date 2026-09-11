import { ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";

import { SAMPLE_CARDS } from "@/lib/mock-battlecards";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** Interactive Sample Gallery: clickable pre-rendered battlecards. */
export function DemoGallery() {
  return (
    <section className="rounded-xl border bg-card p-6 shadow-sm">
      <div className="flex items-start gap-3">
        <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
        <div>
          <h2 className="text-lg font-semibold">Explore without spending a credit</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Two pre-rendered battlecards show exactly what a live research run
            produces — pricing teardowns, verified churn quotes and rebuttals.
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {SAMPLE_CARDS.map((sample) => (
          <Link
            key={sample.slug}
            href={`/samples/${sample.slug}`}
            className="group rounded-xl border bg-card shadow-sm transition-colors hover:border-primary/50 hover:shadow-md"
          >
            <CardHeader>
              <div className="flex items-center gap-2">
                <CardTitle className="group-hover:text-primary">{sample.label}</CardTitle>
              </div>
              <CardDescription>{sample.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">
                  {sample.target} ↔ {sample.competitor}
                </Badge>
                <span className="inline-flex items-center gap-1 text-sm font-medium text-primary group-hover:underline">
                  View preview
                  <ArrowRight className="h-4 w-4" />
                </span>
              </div>
            </CardContent>
          </Link>
        ))}
      </div>
    </section>
  );
}