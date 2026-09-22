"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchCurrentUser, logout, type User } from "@/lib/api";

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
    return <p className="text-sm text-neutral-400">Checking session…</p>;
  }

  if (state.kind === "anonymous") {
    return (
      <div className="flex gap-3 text-sm">
        <Link href="/login" className="text-neutral-700 underline dark:text-neutral-300">
          Log in
        </Link>
        <Link href="/signup" className="text-neutral-700 underline dark:text-neutral-300">
          Sign up
        </Link>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-neutral-600 dark:text-neutral-300">
        Signed in as {state.user.email}
      </span>
      <Link href="/app" className="text-neutral-700 underline dark:text-neutral-300">
        Open workspace
      </Link>
      <button
        onClick={async () => {
          await logout();
          setState({ kind: "anonymous" });
        }}
        className="text-neutral-700 underline dark:text-neutral-300"
      >
        Log out
      </button>
    </div>
  );
}
