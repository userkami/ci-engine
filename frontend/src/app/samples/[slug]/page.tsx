import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { BattlecardView } from "@/components/battlecard-view";
import { getSampleCard } from "@/lib/mock-battlecards";

export const metadata = { title: "Sample battlecard" };

export default async function SamplePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const sample = getSampleCard(slug);
  if (!sample) {
    notFound();
  }

  return (
    <div className="space-y-4">
      <Link
        href="/samples/linear-vs-jira"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground print:hidden"
      >
        <ArrowLeft className="h-4 w-4" />
        Samples
      </Link>
      <BattlecardView
        card={sample.card}
        target={sample.target}
        competitor={sample.competitor}
        demo
      />
    </div>
  );
}