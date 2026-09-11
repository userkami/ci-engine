import { getServerSession } from "next-auth";
import { BarChart3, Radar } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { authOptions } from "@/lib/auth";
import "./globals.css";

export const metadata = {
  title: {
    default: "Craft CI — Competitive Intelligence",
    template: "%s · Craft CI",
  },
  description:
    "Autonomous battlecards: verified pricing teardowns, churn quotes and rebuttal talk tracks for B2B sales.",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const session = await getServerSession(authOptions);

  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col bg-background text-foreground antialiased">
        <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur print:hidden">
          <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Radar className="h-4.5 w-4.5" />
              </span>
              Craft CI
            </Link>
            <div className="flex items-center gap-4 text-sm">
              <Link href="/dashboard" className="text-muted-foreground hover:text-foreground">
                Dashboard
              </Link>
              <Link
                href="/samples/linear-vs-jira"
                className="text-muted-foreground hover:text-foreground"
              >
                Samples
              </Link>
              {session?.user ? (
                <span className="flex items-center gap-2 rounded-full bg-muted px-3 py-1 text-xs">
                  <BarChart3 className="h-3.5 w-3.5 text-primary" />
                  {session.user.name ?? session.user.email ?? "Signed in"}
                  <a
                    href="/api/auth/signout"
                    className="ml-1 text-muted-foreground hover:underline"
                  >
                    Sign out
                  </a>
                </span>
              ) : (
                <a
                  href="/api/auth/signin"
                  className="inline-flex h-8 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                >
                  Sign in
                </a>
              )}
            </div>
          </nav>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
          {children}
        </main>

        <footer className="border-t py-6 text-center text-xs text-muted-foreground print:hidden">
          Craft CI · Autonomous B2B competitive intelligence engine
        </footer>
      </body>
    </html>
  );
}