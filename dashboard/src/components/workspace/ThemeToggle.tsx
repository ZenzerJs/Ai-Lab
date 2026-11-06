import { useEffect, useState } from "react";
import { flushSync } from "react-dom";
import { Moon, Sun } from "lucide-react";

const storageKey = "ai-lab.theme.v1";
type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", theme === "dark" ? "#131116" : "#f5f6fa");
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  );

  useEffect(() => {
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
    const update = (next: Theme) => {
      applyTheme(next);
      setTheme(next);
    };
    const onSystemChange = () => {
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved === "light" || saved === "dark") return;
      } catch {
        /* System preference remains usable when storage is unavailable. */
      }
      update(systemTheme.matches ? "dark" : "light");
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key !== storageKey && event.key !== null) return;
      const next = event.newValue;
      update(
        next === "dark" || next === "light"
          ? next
          : systemTheme.matches
            ? "dark"
            : "light",
      );
    };
    systemTheme.addEventListener("change", onSystemChange);
    window.addEventListener("storage", onStorage);
    return () => {
      systemTheme.removeEventListener("change", onSystemChange);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    const update = () => {
      applyTheme(next);
      flushSync(() => setTheme(next));
      try {
        localStorage.setItem(storageKey, next);
      } catch {
        /* The current tab still supports theme switching. */
      }
    };
    const viewDocument = document as Document & {
      startViewTransition?: (callback: () => void) => {
        finished: Promise<void>;
      };
    };
    if (
      viewDocument.startViewTransition &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      viewDocument.startViewTransition(update).finished.catch(() => {
        /* A subsequent toggle may interrupt the crossfade. */
      });
    } else update();
  };

  return (
    <button
      className="icon-button theme-toggle"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      aria-pressed={theme === "dark"}
      title={`${theme === "dark" ? "Light" : "Dark"} mode`}
      onClick={toggle}
    >
      <span className="theme-icon" key={theme} aria-hidden="true">
        {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
      </span>
    </button>
  );
}
