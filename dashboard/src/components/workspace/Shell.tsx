import { useCallback, useEffect, useRef, useState, ReactNode } from "react";
import {
  ArrowUpRight,
  ArrowDownToLine,
  BookOpen,
  CalendarDays,
  Code2,
  Braces,
  Check,
  ChevronRight,
  FlaskConical,
  Github,
  LayoutDashboard,
  Menu,
  Orbit,
  RefreshCw,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { Destination, snapshotDate } from "../../lib/workspace";
import { ThemeToggle } from "./ThemeToggle";

const navigation = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "tasks", label: "Experiments", icon: FlaskConical },
  { id: "simulator", label: "Model simulator", icon: SlidersHorizontal },
  { id: "sandboxes", label: "Sandboxes", icon: Braces },
  { id: "audit", label: "Evidence ledger", icon: ShieldCheck },
] as const;

interface ShellProps {
  active: Destination;
  generatedAt?: string;
  loading: boolean;
  canExport: boolean;
  onRefresh: () => void;
  onExport: () => void;
  children: ReactNode;
}

export function Shell({
  active,
  generatedAt,
  loading,
  canExport,
  onRefresh,
  onExport,
  children,
}: ShellProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const sidebar = useRef<HTMLElement>(null);
  const focusAfterClose = useRef<"menu" | "main" | null>(null);
  const closeMenu = useCallback((target: "menu" | "main" = "menu") => {
    focusAfterClose.current = target;
    setMenuOpen(false);
  }, []);
  const [exported, setExported] = useState(false);
  const title = navigation.find((item) => item.id === active)?.label;

  useEffect(() => {
    setMenuOpen(false);
    document.getElementById("main-content")?.focus({ preventScroll: true });
  }, [active]);

  useEffect(() => {
    if (menuOpen || !focusAfterClose.current) return;
    const target =
      focusAfterClose.current === "menu"
        ? menuButton.current
        : document.getElementById("main-content");
    target?.focus({ preventScroll: true });
    focusAfterClose.current = null;
  }, [menuOpen]);

  useEffect(() => {
    if (!menuOpen) return;
    sidebar.current?.querySelector<HTMLAnchorElement>("a")?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeMenu();
      }
      if (event.key !== "Tab") return;
      const elements =
        sidebar.current?.querySelectorAll<HTMLElement>("a, button");
      if (!elements?.length) return;
      const first = elements[0],
        last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [menuOpen, closeMenu]);

  useEffect(() => {
    if (!exported) return;
    const timer = window.setTimeout(() => setExported(false), 3000);
    return () => window.clearTimeout(timer);
  }, [exported]);

  return (
    <div className="lab-app">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        Skip to content
      </a>
      {menuOpen && (
        <button
          className="menu-scrim"
          aria-label="Close navigation"
          onClick={() => closeMenu()}
        />
      )}
      <aside
        ref={sidebar}
        id="workspace-navigation"
        className={`lab-sidebar ${menuOpen ? "is-open" : ""}`}
        aria-label="Workspace navigation"
        role={menuOpen ? "dialog" : undefined}
        aria-modal={menuOpen || undefined}
      >
        <div className="brand-row">
          <a
            className="lab-brand"
            href="#overview"
            aria-label="AI-Lab overview"
            onClick={() => closeMenu("main")}
          >
            <span className="brand-icon">
              <Orbit size={27} strokeWidth={1.7} />
            </span>
            <span>
              AI-Lab<span className="brand-subtitle">Context, considered.</span>
            </span>
          </a>
          <button
            className="icon-button mobile-close"
            aria-label="Close navigation"
            onClick={() => closeMenu()}
          >
            <X size={20} />
          </button>
        </div>
        <div className="nav-eyebrow">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation.map(({ id, label, icon: Icon }) => (
            <a
              key={id}
              href={`#${id}`}
              className={`nav-item ${active === id ? "is-active" : ""}`}
              aria-current={active === id ? "page" : undefined}
              onClick={() => closeMenu("main")}
            >
              <Icon size={19} strokeWidth={1.7} />
              <span>{label}</span>
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="open-lab-note">
            <span className="sidebar-note-icon">
              <FlaskConical size={19} />
            </span>
            <strong>A little less guesswork.</strong>
            <p>
              A little more evidence.
              <br />
              Built in the open.
            </p>
            <a
              href="https://github.com/ZenzerJs/Ai-Lab"
              target="_blank"
              rel="noreferrer"
            >
              Explore the project <ArrowUpRight size={15} />
            </a>
          </div>
          <a
            className="sidebar-link"
            href="https://github.com/ZenzerJs/Ai-Lab/tree/main/docs"
            target="_blank"
            rel="noreferrer"
          >
            <BookOpen size={17} /> Documentation <ArrowUpRight size={14} />
          </a>
          <a
            className="sidebar-link"
            href="https://github.com/ZenzerJs/Ai-Lab"
            target="_blank"
            rel="noreferrer"
          >
            <Github size={17} /> View on GitHub <ArrowUpRight size={14} />
          </a>
          <div className="sidebar-foot">
            <Code2 size={13} /> Independent. Open source.
          </div>
        </div>
      </aside>
      <div
        className="lab-workspace"
        {...(menuOpen ? { inert: "", "aria-hidden": true as const } : {})}
      >
        <header className="lab-topbar">
          <div className="breadcrumb">
            <button
              ref={menuButton}
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              aria-controls="workspace-navigation"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(true)}
            >
              <Menu size={21} />
            </button>
            <span className="breadcrumb-root">Workspace</span>
            <ChevronRight size={14} />
            <strong>{title}</strong>
          </div>
          <div className="topbar-actions">
            <ThemeToggle />
            <span className="snapshot-label">
              <CalendarDays size={13} /> Snapshot · {snapshotDate(generatedAt)}
            </span>
            <button
              className="icon-button refresh-button"
              title="Refresh"
              aria-label="Refresh data"
              disabled={loading}
              onClick={onRefresh}
            >
              <RefreshCw size={17} className={loading ? "is-refreshing" : ""} />
            </button>
            <button
              className="button button-outline export-button"
              data-exported={exported || undefined}
              aria-label={exported ? "Report exported" : "Export report"}
              title={exported ? "Report exported" : "Export report"}
              disabled={!canExport}
              onClick={() => {
                onExport();
                setExported(true);
              }}
            >
              {exported ? <Check size={16} /> : <ArrowDownToLine size={16} />}
              <span>{exported ? "Exported" : "Export report"}</span>
            </button>
          </div>
        </header>
        <main id="main-content" tabIndex={-1} className="lab-main">
          {children}
        </main>
        <footer className="lab-footer">
          <span>
            AI-Lab <span className="footer-divider">/</span> Better context.
            Measurable impact.
          </span>
          <span>Open source · OKF v0.2</span>
        </footer>
        <span className="sr-only" role="status">
          {exported ? "Report exported as JSON." : ""}
        </span>
      </div>
    </div>
  );
}
