"use client";

import { useLayoutEffect, useSyncExternalStore } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import {
  applyTheme,
  readTheme,
  setTheme,
  subscribeTheme,
  type ThemeChoice,
} from "@/lib/theme";

const NEXT: Record<ThemeChoice, ThemeChoice> = {
  system: "light",
  light: "dark",
  dark: "system",
};

const ICON = { system: Monitor, light: Sun, dark: Moon };
const LABEL: Record<ThemeChoice, string> = {
  system: "following your system",
  light: "light",
  dark: "dark",
};

/* Cycles system → light → dark. "System" is a real state, not a synonym for
   one of the other two: an operator on a night shift has their OS set up
   already and shouldn't have to re-pick here.

   The choice lives in localStorage, which makes it an external store rather
   than React state — so it's read with useSyncExternalStore. That gives the
   server a defined snapshot ("system") and lets React swap in the real one
   during hydration without a mismatch, which a lazy useState initialiser
   reading localStorage would not. */
export function ThemeToggle() {
  const choice = useSyncExternalStore<ThemeChoice>(
    subscribeTheme,
    readTheme,
    () => "system",
  );

  // React's dev-only Strict Mode remount strips attributes it doesn't own from
  // <html>, including the one the inline script set. Re-apply before paint.
  // No-op in production.
  useLayoutEffect(() => {
    applyTheme(readTheme());
  }, []);

  const Icon = ICON[choice];
  const next = NEXT[choice];

  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      aria-label={`Theme: ${LABEL[choice]}. Switch to ${LABEL[next]}.`}
      title="Change theme"
      className="grid size-8 cursor-pointer place-items-center rounded text-muted transition-colors hover:bg-surface-2 hover:text-ink"
    >
      <Icon size={16} aria-hidden="true" />
    </button>
  );
}
