import React from "react";
import { Cpu, Cloud, Zap } from "lucide-react";
import { AppConfig } from "../../types";

interface HeaderProps {
  config: AppConfig | null;
  activeProvider: "ollama" | "groq";
  onToggleProvider: (p: "ollama" | "groq") => void;
}

export const Header: React.FC<HeaderProps> = ({ config, activeProvider, onToggleProvider }) => {
  const groqAvailable = config?.groq_available ?? false;
  const isOllama = activeProvider === "ollama";

  const ollamaModel = config?.ollama_model ?? "qwen2.5:3b";
  const groqModel = config?.groq_model ?? "groq";

  const activeModel = isOllama ? ollamaModel : groqModel;
  const providerLabel = isOllama ? "Ollama (Local)" : "Groq (Cloud)";

  return (
    <header className="h-14 border-b border-paper-200 bg-paper-50 px-6 flex items-center justify-between shrink-0">
      {/* Title & Brand Context */}
      <div className="flex items-center gap-3">
        <h2 className="font-sans font-semibold text-sm text-ink-900 tracking-tight">
          The Lenny Growth Assistant
        </h2>
        <span className="text-xs text-paper-300 font-sans">•</span>
        <span className="text-xs text-paper-500 font-sans font-medium">Grounded Operator Workbench</span>
      </div>

      {/* Provider Selector & Active Badge */}
      <div className="flex items-center gap-3">
        {/* Toggle pill */}
        <div
          className="flex items-center bg-paper-100 border border-paper-200 rounded-full p-0.5 gap-0.5"
          role="group"
          aria-label="LLM provider selector"
        >
          {/* Ollama option */}
          <button
            id="provider-toggle-ollama"
            onClick={() => onToggleProvider("ollama")}
            className={`
              flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium font-sans
              transition-all duration-150 focus-visible:ring-2 focus-visible:ring-signal-500
              ${isOllama
                ? "bg-ink-800 text-paper-50 shadow-2xs"
                : "text-paper-600 hover:text-ink-900 hover:bg-paper-200/70"
              }
            `}
            title="Use local Ollama model"
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>Local</span>
          </button>

          {/* Groq option */}
          <button
            id="provider-toggle-groq"
            onClick={() => groqAvailable && onToggleProvider("groq")}
            disabled={!groqAvailable}
            className={`
              flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium font-sans
              transition-all duration-150 focus-visible:ring-2 focus-visible:ring-signal-500
              ${!groqAvailable
                ? "text-paper-300 cursor-not-allowed"
                : !isOllama
                  ? "bg-ink-800 text-paper-50 shadow-2xs"
                  : "text-paper-600 hover:text-ink-900 hover:bg-paper-200/70"
              }
            `}
            title={groqAvailable ? "Use Groq cloud API" : "No GROQ_API_KEY configured"}
          >
            <Zap className="w-3.5 h-3.5 text-signal-500" />
            <span>Cloud</span>
            {!groqAvailable && (
              <span className="ml-0.5 text-[10px] text-paper-400">—</span>
            )}
          </button>
        </div>

        {/* Active provider badge */}
        <div className="flex items-center gap-2 bg-paper-100 border border-paper-200 px-3 py-1 rounded-full text-xs font-sans text-paper-700">
          {isOllama ? (
            <Cpu className="w-3.5 h-3.5 text-signal-500" />
          ) : (
            <Cloud className="w-3.5 h-3.5 text-signal-500" />
          )}
          <span className="font-medium text-ink-900">{providerLabel}</span>
          <span className="text-paper-300">•</span>
          <span className="text-paper-500 font-mono text-[11px]">{activeModel}</span>
          <span
            className="w-2 h-2 rounded-full ml-0.5 bg-success-base"
            title="Provider active"
          />
        </div>
      </div>
    </header>
  );
};
