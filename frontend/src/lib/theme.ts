export type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "thinkdesk-theme";
const listeners = new Set<() => void>();

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", theme);
}

export function getTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") return stored;
  } catch {
    // Storage can throw in private browsing / locked-down environments --
    // fall through to the default rather than crashing the page.
  }
  return "system";
}

export function getServerTheme(): Theme {
  return "system";
}

export function setTheme(theme: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Best-effort persistence only; the toggle still works for this tab.
  }
  applyTheme(theme);
  listeners.forEach((listener) => listener());
}

export function subscribeToTheme(callback: () => void): () => void {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

/** Inline script string, inlined into <head> so the correct theme applies
 * before React hydrates -- otherwise a saved dark-mode preference would
 * flash light for a frame on every page load. */
export const THEME_INIT_SCRIPT = `
(function () {
  try {
    var theme = localStorage.getItem("${STORAGE_KEY}");
    if (theme === "light" || theme === "dark") {
      document.documentElement.setAttribute("data-theme", theme);
    }
  } catch (e) {}
})();
`;
