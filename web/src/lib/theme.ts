/* Theme plumbing, shared by the no-flash inline script and the toggle so the
   two can never disagree about the key name or the allowed values. */

export const THEME_KEY = "spotlight-theme";

/** "system" means: no attribute on <html>, let prefers-color-scheme decide. */
export type ThemeChoice = "light" | "dark" | "system";

const CHANGED = "spotlight:themechange";

function isThemeChoice(v: unknown): v is ThemeChoice {
  return v === "light" || v === "dark" || v === "system";
}

/**
 * Runs synchronously in <head>, before the browser paints, so the saved theme
 * is already on <html> by the time any pixel is drawn. Doing this in an effect
 * instead would show a light flash on every load for dark-mode users.
 *
 * Kept as a string because it has to be inlined, not bundled — a deferred
 * module would run after first paint, which is the whole problem.
 */
export const themeInitScript = `(function(){try{var t=localStorage.getItem(${JSON.stringify(
  THEME_KEY,
)});if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t);else document.documentElement.removeAttribute("data-theme")}catch(e){}})()`;

/** Mirrors what the inline script does, for use after hydration. */
export function applyTheme(choice: ThemeChoice) {
  const root = document.documentElement;
  if (choice === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", choice);
}

export function readTheme(): ThemeChoice {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    return isThemeChoice(stored) ? stored : "system";
  } catch {
    return "system";
  }
}

export function setTheme(choice: ThemeChoice) {
  applyTheme(choice);
  try {
    localStorage.setItem(THEME_KEY, choice);
  } catch {
    // Private mode or blocked storage: the theme still applies this session.
  }
  window.dispatchEvent(new Event(CHANGED));
}

/**
 * The theme lives in localStorage, not in React, which makes it an external
 * store. `storage` covers other tabs; the custom event covers this one, since
 * a tab never receives its own `storage` event.
 */
export function subscribeTheme(onChange: () => void) {
  window.addEventListener(CHANGED, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(CHANGED, onChange);
    window.removeEventListener("storage", onChange);
  };
}
