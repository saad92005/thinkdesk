import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // /api/* is handled by src/app/api/[...path]/route.ts, a route handler
  // that proxies to the real backend server-side. A route handler (rather
  // than a plain `rewrites()` entry) is used because it can inject the
  // ngrok-skip-browser-warning header on the outgoing request and forward
  // Set-Cookie correctly -- a bare rewrite can't add request headers.
};

export default nextConfig;
