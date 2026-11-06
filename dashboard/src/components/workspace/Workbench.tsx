import { useState } from "react";
import {
  ArrowUpRight,
  Braces,
  ExternalLink,
  Layers,
  Maximize2,
  RefreshCw,
} from "lucide-react";
import { getPublicUrl } from "../../lib/utils";

const sandboxes = [
  {
    id: "gateway",
    experiment: "EXP-007",
    title: "API gateway topology",
    category: "Systems & telemetry",
    description:
      "Explore traffic flow, change the load, and observe how the gateway responds.",
    governed: "sandbox/exp007_governed/index.html",
    baseline: "sandbox/exp007_vanilla/index.html",
  },
  {
    id: "interview",
    experiment: "EXP-008",
    title: "Interview intelligence",
    category: "Full-stack workspace",
    description:
      "Try a grounded interview flow with evidence inspection and rubric scoring.",
    governed: "sandbox/exp008_governed/index.html",
    baseline: "sandbox/exp008_vanilla/index.html",
  },
  {
    id: "landing",
    experiment: "EXP-005",
    title: "Marketing website",
    category: "Frontend & interaction",
    description:
      "Compare the generated landing pages and explore their interactive components.",
    governed: "sandbox/governed/index.html",
    baseline: "sandbox/vanilla/index.html",
  },
  {
    id: "exhibition",
    experiment: "SHOWCASE",
    title: "The interactive exhibition",
    category: "Portfolio collection",
    description:
      "A wider collection of agent-built interfaces, topology demos, and comparisons.",
    governed: "visual_showcase_2.html",
    baseline: "",
  },
];

export default function Workbench({ active = true }: { active?: boolean }) {
  const [selected, setSelected] = useState(sandboxes[0].id);
  const [arm, setArm] = useState<"governed" | "baseline">("governed");
  const [revision, setRevision] = useState(0);
  const current = sandboxes.find((sandbox) => sandbox.id === selected)!;
  const activeArm = current.baseline ? arm : "governed";
  const url = getPublicUrl(
    activeArm === "baseline" ? current.baseline : current.governed,
  );
  const [wide, setWide] = useState(false);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">BEYOND THE NUMBERS</div>
          <h1>See what the agents built.</h1>
          <p>
            Open the artifacts. Try the interactions. Compare the two approaches
            yourself.
          </p>
        </div>
        <span className="badge badge-purple">
          <Braces size={15} />
          Interactive artifacts
        </span>
      </div>
      <section className="sandbox-grid" aria-label="Choose a sandbox">
        {sandboxes.map((sandbox) => (
          <button
            className={`sandbox-card ${selected === sandbox.id ? "is-selected" : ""}`}
            key={sandbox.id}
            aria-pressed={selected === sandbox.id}
            onClick={() => {
              setSelected(sandbox.id);
              setArm("governed");
            }}
          >
            <span className="sandbox-card-top">
              <span className="eyebrow">{sandbox.experiment}</span>
              <ArrowUpRight size={18} />
            </span>
            <span className="sandbox-category">{sandbox.category}</span>
            <strong>{sandbox.title}</strong>
            <span>{sandbox.description}</span>
          </button>
        ))}
      </section>
      <section
        className={`panel sandbox-preview ${wide ? "preview-wide" : ""}`}
      >
        <div className="sandbox-preview-heading">
          <div>
            <Layers size={19} />
            <h2>{current.title}</h2>
          </div>
          <div className="sandbox-preview-actions">
            {current.baseline && (
              <div className="segmented-control">
                <button
                  aria-pressed={activeArm === "governed"}
                  onClick={() => setArm("governed")}
                >
                  Governed
                </button>
                <button
                  aria-pressed={activeArm === "baseline"}
                  onClick={() => setArm("baseline")}
                >
                  Baseline
                </button>
              </div>
            )}
            <button
              className="icon-button"
              aria-label="Reload sandbox"
              onClick={() => setRevision((value) => value + 1)}
            >
              <RefreshCw size={16} />
            </button>
            <button
              className="icon-button"
              aria-label={wide ? "Restore preview" : "Expand preview"}
              aria-pressed={wide}
              onClick={() => setWide((value) => !value)}
            >
              <Maximize2 size={17} />
            </button>
            <a
              className="button button-outline"
              href={url}
              target="_blank"
              rel="noreferrer"
            >
              Open artifact <ExternalLink size={15} />
            </a>
          </div>
        </div>
        <div className="preview-address">
          <span className="preview-dots">
            <i />
            <i />
            <i />
          </span>
          <span>
            {current.experiment} / {activeArm} artifact
          </span>
          <span className="badge badge-neutral">Sandbox</span>
        </div>
        {active && (
          <iframe
            key={`${selected}-${activeArm}-${revision}`}
            title={`${current.title} — ${activeArm}`}
            src={url}
            sandbox="allow-scripts"
            loading="lazy"
            referrerPolicy="no-referrer"
          />
        )}
        <div className="panel-bottom">
          <span>
            Standalone generated artifact · separate from dashboard metrics
          </span>
          <a className="text-link" href="#audit">
            Inspect run evidence <ArrowUpRight size={15} />
          </a>
        </div>
      </section>
    </>
  );
}
