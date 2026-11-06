import { useMemo, useState } from "react";
import { ArrowUpRight, Check, Cpu, Info, RotateCcw } from "lucide-react";
import { DashboardPayload, ModelCascadeItem, ScaleMode } from "../../types";
import { deriveDataForModel } from "../../lib/recalculate";
import { finite } from "../../lib/workspace";
import { formatCurrency, formatSignedPercent } from "../../lib/formatters";
import { ModelIdentity, ProviderIcon } from "./ProviderIcon";

function scaledCost(item: ModelCascadeItem, scale: ScaleMode) {
  const multiplier = scale === "100m" ? 100 : scale === "10m" ? 10 : 1;
  const baseline =
    scale === "1x"
      ? item.total_baseline_cost_usd
      : finite(item.cost_per_mtok_baseline)
        ? item.cost_per_mtok_baseline * multiplier
        : null;
  const governed =
    scale === "1x"
      ? item.total_icm_cost_usd
      : finite(item.cost_per_mtok_icm)
        ? item.cost_per_mtok_icm * multiplier
        : null;
  return {
    baseline,
    governed,
    saved: finite(baseline) && finite(governed) ? baseline - governed : null,
  };
}

export default function Simulator({ data }: { data: DashboardPayload }) {
  const [selected, setSelected] = useState("recorded");
  const [scale, setScale] = useState<ScaleMode>("1x");
  const derived = useMemo(
    () => deriveDataForModel(data, selected),
    [data, selected],
  );
  const selectedCascade = data.cascade?.find((item) => item.model === selected);
  const recorded = data.cumulative;
  const comparison = selectedCascade
    ? scaledCost(selectedCascade, scale)
    : {
        baseline:
          scale === "1x"
            ? recorded.total_baseline_cost_usd
            : finite(recorded.cost_per_mtok_baseline)
              ? recorded.cost_per_mtok_baseline *
                (scale === "100m" ? 100 : scale === "10m" ? 10 : 1)
              : null,
        governed:
          scale === "1x"
            ? recorded.total_icm_cost_usd
            : finite(recorded.cost_per_mtok_icm)
              ? recorded.cost_per_mtok_icm *
                (scale === "100m" ? 100 : scale === "10m" ? 10 : 1)
              : null,
      };
  const saving =
    finite(comparison.baseline) && finite(comparison.governed)
      ? comparison.baseline - comparison.governed
      : null;
  const isSimulation = selected !== "recorded" || scale !== "1x";
  const pricing = data.pricing.find((rate) => rate.model === selected);
  const noUsableComparison = selected !== "recorded" && !selectedCascade;
  const baseline = noUsableComparison ? null : comparison.baseline;
  const governed = noUsableComparison ? null : comparison.governed;

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">EXPLORE THE POSSIBILITIES</div>
          <h1>Same workload. A different lens.</h1>
          <p>
            Reprice recorded token usage. See how model rates change the
            economics.
          </p>
        </div>
        <span className="badge badge-purple">
          <Cpu size={14} />
          Rate-card simulator
        </span>
      </div>
      <div className="notice notice-purple">
        <Info size={19} />
        <div>
          <strong>Projections, with perspective.</strong>
          <p>
            This reuses source-model token counts. It does not run another model
            or adjust for tokenization, cache thresholds, or thinking-token
            billing. Prices are from the saved snapshot.
          </p>
        </div>
      </div>
      <section className="panel simulator-controls">
        <label className="field-label">
          Model rate card
          <div className="model-select">
            <ProviderIcon model={selected} />
            <select
              aria-label="Model rate card"
              value={selected}
              onChange={(event) => setSelected(event.target.value)}
            >
              <option value="recorded">As recorded · original model</option>
              {data.pricing.map((rate) => (
                <option value={rate.model} key={rate.model}>
                  {rate.model}
                  {rate.pricing_mode === "provider-equivalent"
                    ? " · provider-equivalent"
                    : ""}
                </option>
              ))}
            </select>
          </div>
        </label>
        <fieldset>
          <legend>Token volume</legend>
          <div className="segmented-control">
            {(["1x", "1m", "10m", "100m"] as ScaleMode[]).map((mode) => (
              <button
                key={mode}
                aria-pressed={scale === mode}
                onClick={() => setScale(mode)}
              >
                {mode === "1x" ? "Recorded" : mode.toUpperCase()}
              </button>
            ))}
          </div>
        </fieldset>
        <button
          className="button button-quiet"
          onClick={() => {
            setSelected("recorded");
            setScale("1x");
          }}
        >
          <RotateCcw size={16} />
          Reset
        </button>
      </section>
      <div className="simulation-result">
        <div className="simulation-result-title">
          <span
            className={`badge ${isSimulation || data.is_demo_report ? "badge-amber" : "badge-green"}`}
          >
            {isSimulation
              ? "Simulated projection"
              : data.is_demo_report
                ? "Demo / fixture"
                : data.cumulative.has_measured_data
                  ? "Recorded usage estimate"
                  : "Unverified snapshot"}
          </span>
          <span className="simulation-scope">
            <ProviderIcon model={selected} />
            <span className="mono">
              {selected === "recorded" ? "Original model rates" : selected} ·{" "}
              {scale === "1x"
                ? "Recorded workload"
                : `${scale.toUpperCase()} tokens per arm`}
            </span>
          </span>
        </div>
        <div className="simulation-values">
          <div>
            <span>Baseline spend</span>
            <strong>{formatCurrency(baseline)}</strong>
          </div>
          <div>
            <span>Governed spend</span>
            <strong>{formatCurrency(governed)}</strong>
          </div>
          <div>
            <span>
              {finite(saving) && saving < 0
                ? "Additional spend"
                : "Estimated savings"}
            </span>
            <strong
              className={
                finite(saving) && saving < 0 ? "text-rust" : "text-sea"
              }
            >
              {noUsableComparison ? "—" : formatCurrency(saving)}
            </strong>
          </div>
        </div>
        {pricing && (
          <p className="panel-note">
            Per million tokens: ${pricing.input_usd_per_mtok} input · $
            {pricing.cache_read_usd_per_mtok} cache · $
            {pricing.output_usd_per_mtok} output. Saved{" "}
            {pricing.fetched_at?.slice(0, 10)}.{" "}
            {pricing.source_url && (
              <a href={pricing.source_url} target="_blank" rel="noreferrer">
                Rate source <ArrowUpRight size={13} />
              </a>
            )}
          </p>
        )}
        {pricing?.pricing_mode === "provider-equivalent" && (
          <p className="notice notice-amber">
            Provider-equivalent simulation. Direct benchmark cost was $0. These
            estimates are excluded from measured savings.{" "}
            {pricing.provider_note}
          </p>
        )}
        {selected !== "recorded" && derived && (
          <p className="panel-note">
            Repriced {derived.runs.length} source records. Unavailable costs
            remain unavailable.
          </p>
        )}
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Compare model economics</h2>
            <p>
              {scale === "1x"
                ? "Original workload"
                : `Normalized to ${scale.toUpperCase()} tokens per arm`}{" "}
              · choose a model to explore
            </p>
          </div>
          <span className="badge badge-purple">Simulation</span>
        </div>
        <div
          className="table-scroll"
          role="region"
          aria-label="Model pricing comparison"
          tabIndex={0}
        >
          <table className="data-table model-table">
            <caption className="sr-only">
              Model rate-card simulations. All amounts are US dollars.
            </caption>
            <thead>
              <tr>
                <th scope="col">Model</th>
                <th scope="col">Input / cache / output per M</th>
                <th scope="col">Baseline</th>
                <th scope="col">Governed</th>
                <th scope="col">Savings</th>
                <th scope="col">Explore</th>
              </tr>
            </thead>
            <tbody>
              {(data.cascade || []).map((item) => {
                const cost = scaledCost(item, scale);
                const reduction =
                  finite(cost.baseline) &&
                  cost.baseline > 0 &&
                  finite(cost.saved)
                    ? (cost.saved / cost.baseline) * 100
                    : null;
                return (
                  <tr
                    key={item.model}
                    className={selected === item.model ? "is-selected" : ""}
                  >
                    <th scope="row">
                      <ModelIdentity model={item.model} />
                      {item.pricing_mode === "provider-equivalent" && (
                        <span className="cell-subtitle">
                          Provider-equivalent · simulated
                        </span>
                      )}
                    </th>
                    <td className="mono rate-cell">
                      ${item.input_usd_per_mtok} / $
                      {item.cache_read_usd_per_mtok} / $
                      {item.output_usd_per_mtok}
                    </td>
                    <td>{formatCurrency(cost.baseline)}</td>
                    <td>{formatCurrency(cost.governed)}</td>
                    <td
                      className={
                        finite(cost.saved) && cost.saved < 0
                          ? "text-rust"
                          : "text-sea"
                      }
                    >
                      {formatCurrency(cost.saved)}
                      <span className="cell-subtitle">
                        {formatSignedPercent(reduction)}
                      </span>
                    </td>
                    <td>
                      <button
                        className={`button ${selected === item.model ? "button-primary" : "button-outline"}`}
                        onClick={() => setSelected(item.model)}
                        aria-label={`Simulate ${item.model}`}
                        aria-pressed={selected === item.model}
                      >
                        {selected === item.model ? (
                          <Check size={15} />
                        ) : (
                          <ArrowUpRight size={15} />
                        )}{" "}
                        {selected === item.model ? "Selected" : "Simulate"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!data.cascade?.length && (
            <p className="empty-inline">
              No model comparisons available in this snapshot.
            </p>
          )}
        </div>
      </section>
    </>
  );
}
