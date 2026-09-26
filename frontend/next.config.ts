import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Lets one public tunnel (e.g. ngrok) front both the frontend and the
  // backend: the browser only ever talks to this same origin, and Next's
  // own server forwards anything under /api to the FastAPI backend
  // running locally. Only takes effect when NEXT_PUBLIC_API_URL is set to
  // a relative path (e.g. "/api") -- see docs/deployment.md.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
