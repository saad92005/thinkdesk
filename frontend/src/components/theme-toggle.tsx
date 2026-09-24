"use client";

import { useSyncExternalStore } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { getServerTheme, getTheme, setTheme, subscribeToTheme, type Theme } from "@/lib/theme";

const NEXT: Record<Theme, Theme> = { light: "dark", dark: "system", system: "light" };
const ICON: Record<Theme, typeof Sun> = { light: Sun, dark: Moon, system: Monitor };
const LABEL: Record<Theme, string> = { light: "Light theme", dark: "Dark theme", system: "System theme" };

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeToTheme, getTheme, getServerTheme);
  const Icon = ICON[theme];

  return (
    <button
      onClick={() => setTheme(NEXT[theme])}
      aria-label={`${LABEL[theme]} — click to change`}
      title={LABEL[theme]}
      className="flex h-8 w-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-black/[.04] hover:text-foreground dark:hover:bg-white/[.06]"
    >
      <Icon className="h-4 w-4" strokeWidth={1.75} />
    </button>
  );
}
