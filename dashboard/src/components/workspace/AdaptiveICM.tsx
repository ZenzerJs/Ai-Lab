import { ArrowRight, Layers3 } from "lucide-react";
import { formatArm } from "../../lib/formatters";

/** Routing guidance, deliberately separate from the recorded benchmark results. */
export default function AdaptiveICM() {
  return (
    <section className="adaptive-icm panel" aria-label="Adaptive ICM routing guidance">
      <div className="adaptive-heading">
        <div>
          <span className="eyebrow"><Layers3 size={14} /> ADAPTIVE ICM</span>
          <h2>The right amount of structure.</h2>
        </div>
        <span className="badge badge-purple">~150 LOC / 2+ file break-even</span>
      </div>
      <div className="adaptive-regimes">
        <div>
          <span className="badge badge-purple">{formatArm("icm_lite")}</span>
          <h3>Micro-tasks</h3>
          <p>&lt;150 LOC <strong>and</strong> exactly 1 target file.</p>
          <span className="adaptive-detail">One compact contract. Less fixed governance overhead.</span>
        </div>
        <ArrowRight className="adaptive-arrow" size={22} aria-hidden="true" />
        <div>
          <span className="badge badge-purple">{formatArm("icm")}</span>
          <h3>Larger or multi-file work</h3>
          <p>≥150 LOC <strong>or</strong> 2+ target files.</p>
          <span className="adaptive-detail">Full five-stage governance. Unknown scope defaults here, too.</span>
        </div>
      </div>
      <p className="adaptive-note">
        <span className="badge badge-neutral">{formatArm("baseline")}</span>
        Unconstrained comparison arm. These are auto-routing rules informed by
        the empirical break-even range, not a guarantee of savings or measured ICM-Lite results.
      </p>
    </section>
  );
}
