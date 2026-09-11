import { getServerSession } from "next-auth";
import { notFound, redirect } from "next/navigation";

import { BattlecardView } from "@/components/battlecard-view";
import { Card, CardContent } from "@/components/ui/card";
import { authOptions } from "@/lib/auth";
import { BackendRequestError, getBattlecard } from "@/lib/backend";

export const metadata = { title: "Battlecard" };

export default async function BattlecardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    redirect(`/api/auth/signin?callbackUrl=/battlecard/${id}`);
  }

  let record;
  try {
    record = await getBattlecard(id);
  } catch (err) {
    if (err instanceof BackendRequestError && err.status === 404) {
      notFound();
    }
    if (err instanceof BackendRequestError && err.status === 403) {
      return (
        <Card>
          <CardContent className="space-y-2 py-8">
            <h1 className="text-lg font-semibold">Battlecard unavailable</h1>
            <p className="text-sm text-muted-foreground">
              This battlecard belongs to another account.
            </p>
          </CardContent>
        </Card>
      );
    }
    throw err;
  }

  return (
    <BattlecardView
      card={record.report_data}
      target={record.target_company}
      competitor={record.competitor}
    />
  );
}