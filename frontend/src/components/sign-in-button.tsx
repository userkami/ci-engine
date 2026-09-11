"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * "Sign in with Google" — the ONLY element that may start the OAuth flow.
 *
 * `lib/auth.ts` registers `/` as the custom sign-in page, so any Link to
 * `/api/auth/signin` merely bounces back to this page (redirect loop). The
 * flow must be triggered client-side via `signIn("google")`, which POSTs the
 * CSRF token and redirects to Google's consent screen. The `callbackUrl`
 * query (added by the /dashboard redirect) is honored and passed through.
 */
export function SignInButton({ label = "Sign in with Google" }: { label?: string }) {
  const searchParams = useSearchParams();
  const [pending, setPending] = useState(false);

  const handleClick = () => {
    setPending(true);
    // Same-origin absolute URLs are allowed by NextAuth; anything else is
    // ignored by it in favor of the configured NEXTAUTH_URL origin.
    const callbackUrl = searchParams.get("callbackUrl") ?? "/dashboard";
    void signIn("google", { callbackUrl });
  };

  return (
    <Button size="lg" onClick={handleClick} disabled={pending}>
      {pending ? "Redirecting to Google…" : label}
      <ArrowRight className="h-4 w-4" />
    </Button>
  );
}
