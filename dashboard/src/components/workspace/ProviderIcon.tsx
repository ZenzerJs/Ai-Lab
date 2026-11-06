import { Cpu, Orbit } from "lucide-react";
import { getPublicUrl } from "../../lib/utils";

const providers = {
  google: { name: "Google", asset: "google.png" },
  openai: { name: "OpenAI", asset: "openai.svg" },
  anthropic: { name: "Anthropic", asset: "anthropic.svg" },
  zai: { name: "Z.ai / GLM", asset: "zai.svg" },
};

export function providerForModel(model: string) {
  const name = model.toLowerCase();
  if (/^(gemini|google)/.test(name)) return providers.google;
  if (/^(gpt|chatgpt|openai|o\d)/.test(name)) return providers.openai;
  if (/^(claude|anthropic)/.test(name)) return providers.anthropic;
  if (/^(glm|z[.-]?ai|chatglm)/.test(name)) return providers.zai;
  return undefined;
}

export function ProviderIcon({ model }: { model: string }) {
  const provider = providerForModel(model);
  return (
    <span
      className={`provider-icon ${provider ? "provider-mark" : "provider-generic"} ${provider === providers.openai || provider === providers.anthropic ? "provider-monochrome" : ""}`}
      data-provider={provider?.name}
      role="img"
      aria-label={
        provider?.name || (model === "recorded" ? "Recorded model" : "Model")
      }
      title={provider?.name}
    >
      {provider ? (
        <img
          src={getPublicUrl(`providers/${provider.asset}`)}
          alt=""
          width={20}
          height={20}
          decoding="async"
        />
      ) : model === "recorded" ? (
        <Orbit size={19} />
      ) : (
        <Cpu size={19} />
      )}
    </span>
  );
}

export function ModelIdentity({ model }: { model: string }) {
  return (
    <span className="model-identity">
      <ProviderIcon model={model} />
      <span>
        <strong>{model}</strong>
        <span className="cell-subtitle">
          {providerForModel(model)?.name || "Recorded model"}
        </span>
      </span>
    </span>
  );
}
