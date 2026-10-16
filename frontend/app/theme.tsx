"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Theme = "dark" | "light";
type ThemeContextValue = { theme: Theme; setTheme: (next: Theme) => void };

const ThemeContext = createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "writlynx-theme";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setCurrentTheme] = useState<Theme>("dark");

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    const initial: Theme = saved === "light" ? "light" : "dark";
    setCurrentTheme(initial);
    document.documentElement.dataset.theme = initial;
  }, []);

  const setTheme = (next: Theme) => {
    setCurrentTheme(next);
    document.documentElement.dataset.theme = next;
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // The selected theme still works for this page when storage is unavailable.
    }
  };

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export function ThemeToggle() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("ThemeToggle must be rendered inside ThemeProvider.");

  return (
    <div className="theme-toggle" role="group" aria-label="Choose colour theme">
      <button
        type="button"
        className={context.theme === "light" ? "theme-option is-selected" : "theme-option"}
        aria-pressed={context.theme === "light"}
        onClick={() => context.setTheme("light")}
      >
        <span aria-hidden="true">☼</span> Light
      </button>
      <button
        type="button"
        className={context.theme === "dark" ? "theme-option is-selected" : "theme-option"}
        aria-pressed={context.theme === "dark"}
        onClick={() => context.setTheme("dark")}
      >
        <span aria-hidden="true">◐</span> Dark
      </button>
    </div>
  );
}
