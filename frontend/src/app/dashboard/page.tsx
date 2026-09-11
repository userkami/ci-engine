import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { CreditTracker } from "@/components/credit-tracker";
import { DemoGallery } from "@/components/demo-gallery";
import { ResearchRunner } from "@/components/research-runner";
import { authOptions } from "@/lib/auth";
import { provisionBackendIdentity } from "@/lib/backend";

export const metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    redirect("/api/auth/signin?callbackUrl=/dashboard");
  }
  const { balance } = await provisionBackendIdentity();
  const user = {
    id: session.user.id,
    name: session.user.name,
    email: session.user.email,
    image: session.user.image,
  };

  return (
    <div className="space-y-6">
      {/* SPEC §7: default 5 free credits per account. */}
      <CreditTracker user={user} balance={balance} />
      <ResearchRunner />
      <DemoGallery />
    </div>
  );
}
