/**
 * Next.js configuration for the CI frontend.
 *
 * - `output: "standalone"` matches the multi-stage standalone Dockerfile.
 * - SSE uses an authenticated route handler with a runtime backend URL.
 * - Radix packages ship source; Next transpiles them.
 *
 * BACKEND_PROXY_URL is read by server routes, not embedded during build.
 */

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: [
    "@radix-ui/react-tabs",
    "@radix-ui/react-dialog",
    "@radix-ui/react-progress",
  ],
};

export default nextConfig;
