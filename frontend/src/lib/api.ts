/**
 * Client-safe URL helpers. The browser talks to the backend through the
 * Next.js rewrite proxy (next.config.mjs) so EventSource streams work
 * without CORS, and all state-changing calls go through /api/actions.
 */
export const sseStreamUrl = (jobId: string): string =>
  `/api/backend/jobs/${encodeURIComponent(jobId)}/stream`;

export const actionUrl = (path: string): string => `/api/actions/${path}`;