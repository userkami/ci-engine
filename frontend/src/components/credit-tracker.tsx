import { Coins, UserRound } from "lucide-react";

import type { AppUser } from "@/types";

/** Credit Tracker Header: profile on the left, balance pill on the right. */
export function CreditTracker({
  user,
  balance = 5,
}: {
  user: AppUser;
  balance?: number;
}) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-xl border bg-card p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-primary/10">
          {user.image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={user.image}
              alt=""
              className="h-10 w-10 rounded-full object-cover"
            />
          ) : (
            <UserRound className="h-6 w-6 text-primary" />
          )}
        </div>
        <div>
          <p className="font-medium">{user.name ?? user.email ?? "Anonymous"}</p>
          <p className="text-xs text-muted-foreground">
            {user.email ?? "Signed in via Google"}
          </p>
        </div>
      </div>

      <div
        className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2"
        title="Each research job costs 5 credits"
      >
        <Coins className="h-4 w-4 text-amber-500" />
        <span className="font-semibold tabular-nums">{balance}</span>
        <span className="text-xs text-muted-foreground">credits left</span>
      </div>
    </header>
  );
}