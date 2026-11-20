import { Cpu, Orbit } from "lucide-react";
import { getPublicUrl } from "../../lib/utils";

const providers: Record<string, { name: string; asset?: string }> = {
  google: { name: "Google", asset: "google.png" },
  openai: { name: "OpenAI", asset: "openai.svg" },
  anthropic: { name: "Anthropic", asset: "anthropic.svg" },
  zai: { name: "Z.ai / GLM", asset: "zai.svg" },
  deepseek: { name: "DeepSeek" },
  xai: { name: "xAI" },
  qwen: { name: "Alibaba / Qwen" },
};

export function providerForModel(model: string) {
  const name = model.toLowerCase();
  if (/^(gemini|google)/.test(name)) return providers.google;
  if (/^(gpt|chatgpt|openai|o\d)/.test(name)) return providers.openai;
  if (/^(claude|anthropic)/.test(name)) return providers.anthropic;
  if (/^(glm|z[.-]?ai|chatglm)/.test(name)) return providers.zai;
  if (/^deepseek/.test(name)) return providers.deepseek;
  if (/^(grok|xai)/.test(name)) return providers.xai;
  if (/^(qwen|alibaba)/.test(name)) return providers.qwen;
  return undefined;
}

export function ProviderIcon({ model }: { model: string }) {
  const provider = providerForModel(model);
  return (
    <span
      className={`provider-icon ${provider?.asset ? "provider-mark" : "provider-generic"} ${provider === providers.openai || provider === providers.anthropic ? "provider-monochrome" : ""}`}
      data-provider={provider?.name}
      role="img"
      aria-label={
        provider?.name || (model === "recorded" ? "Recorded model" : "Model")
      }
      title={provider?.name}
    >
      {provider?.asset ? (
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
