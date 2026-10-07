import { NextRequest, NextResponse } from "next/server";

// The backend's real origin, reachable from wherever this Next.js server
// runs (locally: the backend on localhost; on Vercel: the public ngrok
// tunnel). Never exposed to the browser -- only used in this server-side
// proxy.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

// Every browser request to this app's own /api/* is forwarded here,
// server-to-server, to the real backend. This keeps the session cookie
// first-party (set by this app's own domain, not a separate backend
// domain), which is required for it to survive browsers that block
// cross-site cookies (Safari by default, and increasingly Chrome/Firefox/
// Brave with stricter privacy settings).
async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const target = new URL(`${BACKEND_ORIGIN}/${path.join("/")}${request.nextUrl.search}`);

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  // Defeats ngrok's free-tier HTML interstitial on this server-to-server leg.
  headers.set("ngrok-skip-browser-warning", "true");

  const hasBody = !["GET", "HEAD"].includes(request.method);

  const backendResponse = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    redirect: "manual",
    // Required by undici/Node fetch when streaming a request body.
    duplex: hasBody ? "half" : undefined,
  } as RequestInit);

  const responseHeaders = new Headers(backendResponse.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("transfer-encoding");
  responseHeaders.delete("content-length");
  responseHeaders.delete("connection");

  const response = new NextResponse(backendResponse.body, {
    status: backendResponse.status,
    headers: responseHeaders,
  });

  const setCookie =
    typeof backendResponse.headers.getSetCookie === "function"
      ? backendResponse.headers.getSetCookie()
      : backendResponse.headers.get("set-cookie")
        ? [backendResponse.headers.get("set-cookie") as string]
        : [];
  response.headers.delete("set-cookie");
  for (const cookie of setCookie) {
    response.headers.append("set-cookie", cookie);
  }

  return response;
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}
export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}
export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}
export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}
export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}
