import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react";
import { DashboardPayload } from "./types";
import { getPublicUrl } from "./lib/utils";
import { Destination, downloadJson, readDestination } from "./lib/workspace";
import { Shell } from "./components/workspace/Shell";
import { Overview } from "./components/workspace/Overview";

const Experiments = lazy(() => import("./components/workspace/Experiments"));
const Simulator = lazy(() => import("./components/workspace/Simulator"));
const Evidence = lazy(() => import("./components/workspace/Evidence"));
const Workbench = lazy(() => import("./components/workspace/Workbench"));

function LoadingView() {
  return (
    <div
      className="workspace-loading"
      role="status"
      aria-label="Loading workspace"
    >
      <span className="eyebrow">GETTING THE LAB READY</span>
      <div className="loading-title" />
      <div className="loading-hero" />
      <div className="loading-cards">
        <div />
        <div />
        <div />
      </div>
      <span className="sr-only">Loading benchmark snapshot…</span>
    </div>
  );
}

export function App() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState(readDestination);
  const [visited, setVisited] = useState<Destination[]>(() => [
    readDestination(),
  ]);
  const request = useRef<AbortController | null>(null);
  const [refreshCount, setRefreshCount] = useState(0);

  const fetchData = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(getPublicUrl("data.json"), {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok)
        throw new Error(`Snapshot request failed (HTTP ${response.status}).`);
      const json: DashboardPayload = await response.json();
      if (
        !json ||
        !Array.isArray(json.runs) ||
        !Array.isArray(json.tasks) ||
        !json.cumulative ||
        !Array.isArray(json.pricing)
      ) {
        throw new Error("The snapshot is missing required benchmark records.");
      }
      if (controller.signal.aborted) return;
      setData(json);
      setRefreshCount((count) => count + 1);
    } catch (cause) {
      if (controller.signal.aborted) return;
      setError(
        cause instanceof Error
          ? cause.message
          : "The benchmark snapshot could not be loaded.",
      );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    return () => request.current?.abort();
  }, [fetchData]);
  useEffect(() => {
    const navigate = () => {
      const destination = readDestination();
      setActive(destination);
      setVisited((pages) =>
        pages.includes(destination) ? pages : [...pages, destination],
      );
      window.scrollTo({ top: 0, behavior: "instant" });
    };
    window.addEventListener("hashchange", navigate);
    return () => window.removeEventListener("hashchange", navigate);
  }, []);

  const demo =
    data &&
    (data.is_demo_report ||
      data.is_simulation ||
      !data.cumulative.has_measured_data);
  const empty = data && !data.runs.length && !data.tasks.length;
  return (
    <Shell
      active={active}
      generatedAt={data?.generated_at}
      loading={loading}
      canExport={Boolean(data)}
      onRefresh={fetchData}
      onExport={() => data && downloadJson(data, "ai-lab-report.json")}
    >
      {error && (
        <div className="notice notice-error" role="alert">
          <AlertTriangle size={20} />
          <div>
            <strong>Couldn't load the latest snapshot.</strong>
            <p>
              {error} Check your connection and try again.
              {data ? " Showing the last loaded snapshot." : ""}
            </p>
          </div>
          <button
            className="button button-outline"
            onClick={fetchData}
            disabled={loading}
          >
            <RefreshCw size={15} />
            Retry
          </button>
        </div>
      )}
      {demo && (
        <div
          className="notice notice-amber"
          data-testid={
            data?.is_demo_report
              ? "demo-fixture-banner"
              : "evidence-status-banner"
          }
        >
          <AlertTriangle size={20} />
          <div>
            <strong>
              {data?.is_demo_report
                ? "Demo / fixture data · measured headlines unavailable"
                : data?.is_simulation
                  ? "Simulation snapshot · measured headlines unavailable"
                  : "Measured headlines unavailable"}
            </strong>
            <p>
              This snapshot has no eligible measured headline results. Inspect
              record provenance in the evidence ledger.
            </p>
          </div>
        </div>
      )}
      {empty && (
        <div className="notice notice-purple">
          <CheckCircle2 size={20} />
          <div>
            <strong>Your workspace is ready for its first result.</strong>
            <p>
              No experiment records in this snapshot. Add verified runs to the
              project, then refresh the data.
            </p>
          </div>
        </div>
      )}
      {loading && !data ? (
        <LoadingView />
      ) : (
        visited.map((page) => (
          <div key={page} hidden={active !== page} className="workspace-page">
            <Suspense fallback={<LoadingView />}>
              {page === "sandboxes" ? (
                <Workbench active={active === page} />
              ) : data ? (
                <>
                  {page === "overview" && <Overview data={data} />}
                  {page === "tasks" && <Experiments data={data} />}
                  {page === "simulator" && <Simulator data={data} />}
                  {page === "audit" && <Evidence data={data} />}
                </>
              ) : (
                !error && <LoadingView />
              )}
            </Suspense>
          </div>
        ))
      )}
      <span className="sr-only" role="status">
        {!loading && data && refreshCount > 1
          ? `Snapshot refreshed. ${data.runs.length} records loaded.`
          : ""}
      </span>
    </Shell>
  );
}
