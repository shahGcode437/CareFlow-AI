import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

/**
 * Small home-grown theme provider — no extra dependencies. Three
 * user-visible modes:
 *
 *   - "light" and "dark" force the theme explicitly.
 *   - "system" follows `prefers-color-scheme` and stays reactive to
 *     OS-level changes while it's the active choice.
 *
 * The chosen mode is persisted in localStorage under `cf-theme`; the
 * effective (resolved) theme is applied by toggling the `dark` class on
 * `<html>`, which is what the Tailwind v4 `@custom-variant dark` rule
 * in `index.css` reads.
 */

export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

interface ThemeContextValue {
  mode: ThemeMode;
  resolved: ResolvedTheme;
  setMode: (mode: ThemeMode) => void;
  /** Cycles light → dark → system for the header toggle button. */
  cycle: () => void;
}

const STORAGE_KEY = "cf-theme";
const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function readStoredMode(): ThemeMode {
  if (typeof window === "undefined") return "system";
  const raw = window.localStorage.getItem(STORAGE_KEY);
  return raw === "light" || raw === "dark" || raw === "system" ? raw : "system";
}

function getSystemPrefersDark(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyDocumentTheme(resolved: ResolvedTheme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(readStoredMode);
  const [systemPrefersDark, setSystemPrefersDark] = useState<boolean>(
    getSystemPrefersDark,
  );

  const resolved: ResolvedTheme =
    mode === "system" ? (systemPrefersDark ? "dark" : "light") : mode;

  useEffect(() => {
    applyDocumentTheme(resolved);
  }, [resolved]);

  // Track OS-level preference so "system" stays live.
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = (event: MediaQueryListEvent) => {
      setSystemPrefersDark(event.matches);
    };
    mq.addEventListener("change", listener);
    return () => mq.removeEventListener("change", listener);
  }, []);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
  }, []);

  const cycle = useCallback(() => {
    setModeState((current) => {
      const next: ThemeMode =
        current === "light" ? "dark" : current === "dark" ? "system" : "light";
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, next);
      }
      return next;
    });
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ mode, resolved, setMode, cycle }),
    [mode, resolved, setMode, cycle],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a <ThemeProvider>.");
  }
  return ctx;
}
