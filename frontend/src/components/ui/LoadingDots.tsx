import React from "react";

export const LoadingDots: React.FC<{ label?: string }> = ({ label = "Thinking…" }) => {
  return (
    <div className="flex items-center gap-2 text-xs font-sans text-paper-500 py-2">
      <span className="flex gap-1 items-center">
        <span className="w-1.5 h-1.5 rounded-full bg-signal-500 animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="w-1.5 h-1.5 rounded-full bg-signal-500 animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="w-1.5 h-1.5 rounded-full bg-signal-500 animate-bounce" style={{ animationDelay: "300ms" }} />
      </span>
      <span>{label}</span>
    </div>
  );
};
