/**
 * Next.js configuration for the CI frontend.
 *
 * - `output: "standalone"` matches the multi-stage standalone Dockerfile.
 * - `/api/backend/:path*` is reverse-proxied to the FastAPI backend so the
 *   browser can open SSE streams (EventSource) without CORS headers.
 * - Radix packages ship source; Next transpiles them.
 *
 * BACKEND_PROXY_URL resolves to `http://backend:8000` inside the compose
 * network and `http://localhost:8000` for local development.
 */
const BACKEND_PROXY_URL = process.env.BACKEND_PROXY_URL ?? "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: [
    "@radix-ui/react-tabs",
    "@radix-ui/react-dialog",
    "@radix-ui/react-progress",
  ],
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${BACKEND_PROXY_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;