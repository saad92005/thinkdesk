"use client";

import { useEffect, useState } from "react";
import { LinkButton } from "@/components/ui/button";
import { fetchCurrentUser, type User } from "@/lib/api";

type State = { kind: "loading" } | { kind: "anonymous" } | { kind: "authenticated"; user: User };

export function AuthStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchCurrentUser()
      .then((user) => {
        if (cancelled) return;
        setState(user ? { kind: "authenticated", user } : { kind: "anonymous" });
      })
      .catch(() => {
        if (!cancelled) setState({ kind: "anonymous" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === "loading") {
    return <div className="h-9 w-24" />;
  }

  if (state.kind === "anonymous") {
    return (
      <div className="flex items-center gap-3">
        <LinkButton href="/login" variant="ghost" size="sm">
          Log in
        </LinkButton>
        <LinkButton href="/signup" variant="primary" size="sm">
          Get started free
        </LinkButton>
      </div>
    );
  }

  return (
    <LinkButton href="/app" variant="primary" size="sm">
      Open workspace
    </LinkButton>
  );
}
