import { Suspense } from "react";
import { getServerSession } from "next-auth";
import { ArrowRight, Search, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";

import { DemoGallery } from "@/components/demo-gallery";
import { SignInButton } from "@/components/sign-in-button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { authOptions } from "@/lib/auth";

export default async function LandingPage() {
  const session = await getServerSession(authOptions);

  return (
    <div className="space-y-12">
      <section className="flex flex-col items-start gap-4">
        <Badge variant="secondary">Autonomous B2B competitive intelligence</Badge>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Win every deal with a battlecard your rep can actually use.
        </h1>
        <p className="max-w-2xl text-muted-foreground">
          Craft CI researches any competitor — pricing teardowns, verified
          churn quotes from G2/Reddit, and objection rebuttal scripts — and
          assembles a citation-backed battlecard in minutes, not weeks.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          {session?.user ? (
            <Link
              href="/dashboard"
              className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-8 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Open dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          ) : (
            <Suspense fallback={null}>
              <SignInButton />
            </Suspense>
          )}
          <Link
            href="/samples/linear-vs-jira"
            className="inline-flex h-10 items-center gap-2 rounded-md border px-4 text-sm font-medium hover:bg-accent"
          >
            See a sample battlecard
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-4 w-4 text-primary" /> Research
            </CardTitle>
            <CardDescription>
              An agent plans targeted queries for pricing, complaints and
              changelogs — then searches and scrapes the live web.
            </CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" /> Verify
            </CardTitle>
            <CardDescription>
              Evidence is checked for real pricing figures and verbatim
              customer quotes, with targeted retries when gaps are found.
            </CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" /> Synthesize
            </CardTitle>
            <CardDescription>
              A heavy model produces the final battlecard with source links,
              rebuttal talk tracks and landmine questions.
            </CardDescription>
          </CardHeader>
        </Card>
      </section>

      <DemoGallery />
    </div>
  );
}