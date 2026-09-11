/**
 * NextAuth module augmentation (TS module declaration merging).
 *
 * The CI backend identifies users by their UUID (`users.id`, SPEC §4). We
 * propagate that id through the JWT (via the `jwt` callback in lib/auth.ts)
 * and expose it on `session.user.id` for server components and API routes.
 */
import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: {
      /** Backend users.id (UUID) — mirrored from token.sub. */
      id: string;
    } & DefaultSession["user"];
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    /** Backend users.id (UUID). */
    id: string;
  }
}
