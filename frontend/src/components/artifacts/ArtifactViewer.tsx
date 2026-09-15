import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, FileText, Code2, X } from "lucide-react";
import { Artifact } from "../../types";
import { Alert } from "../ui/Alert";
import { Button } from "../ui/Button";

interface ArtifactViewerProps {
  artifact: Artifact | null;
  onClose: () => void;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ artifact, onClose }) => {
  const [viewMode, setViewMode] = useState<"rendered" | "raw">("rendered");
  const [copied, setCopied] = useState(false);

  if (!artifact) {
    return null;
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const validation = artifact.metadata?.validation_status;

  return (
    <div className="flex flex-col h-full bg-paper-50 border-l border-paper-200 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-paper-200 bg-paper-100/70 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-4 h-4 text-signal-500 shrink-0" />
          <h3 className="font-sans font-semibold text-sm text-ink-900 truncate max-w-[260px]">
            {artifact.title || "Artifact Viewer"}
          </h3>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* View mode toggle */}
          <div className="flex bg-paper-200 p-0.5 rounded-sm text-xs font-sans">
            <button
              onClick={() => setViewMode("rendered")}
              className={`px-2.5 py-1 rounded-sm font-medium transition-colors ${viewMode === "rendered"
                  ? "bg-paper-50 text-ink-900 shadow-2xs font-semibold"
                  : "text-paper-600 hover:text-ink-900"
                }`}
            >
              Rendered
            </button>
            <button
              onClick={() => setViewMode("raw")}
              className={`px-2.5 py-1 rounded-sm font-medium transition-colors ${viewMode === "raw"
                  ? "bg-paper-50 text-ink-900 shadow-2xs font-semibold"
                  : "text-paper-600 hover:text-ink-900"
                }`}
            >
              Raw
            </button>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            title="Copy Content"
            className="h-7 px-2"
          >
            {copied ? (
              <span className="flex items-center gap-1 text-signal-500 font-sans text-xs">
                <Check className="w-3.5 h-3.5" /> Copied
              </span>
            ) : (
              <Copy className="w-3.5 h-3.5 text-paper-600" />
            )}
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            title="Close Pane"
            className="h-7 px-2"
          >
            <X className="w-4 h-4 text-paper-500 hover:text-ink-900" />
          </Button>
        </div>
      </div>

      {/* Validation Status Notice (Displayed when structural rules need review) */}
      {validation && !validation.passed && (
        <div className="p-4 border-b border-warning-base/30 bg-warning-light/40 shrink-0">
          <Alert variant="warning" title="Structural Notice">
            <p className="mb-1">
              This draft generated structural discrepancies:
            </p>
            <ul className="list-disc pl-4 space-y-0.5 mb-1.5 font-mono text-[11px]">
              {validation.unmet_criteria.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
            <p className="text-[11px] text-paper-600">
              Content is rendered below and remains ready for direct editing or copying.
            </p>
          </Alert>
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-8">
        {viewMode === "rendered" ? (
          artifact.type === "html" ? (
            <iframe
              title={artifact.title || "HTML Artifact"}
              sandbox="allow-scripts"
              srcDoc={artifact.content}
              className="w-full h-full min-h-[600px] border border-paper-200 rounded-base bg-white shadow-2xs"
            />
          ) : (
            <article className="prose-editorial mx-auto">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
            </article>
          )
        ) : (
          <pre className="font-mono text-xs text-ink-900 bg-paper-100/90 p-4 rounded-base border border-paper-200 overflow-x-auto whitespace-pre-wrap leading-relaxed">
            {artifact.content}
          </pre>
        )}
      </div>
    </div>
  );
};
