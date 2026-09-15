import React from "react";

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ error = false, className = "", ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={`w-full resize-none p-2.5 rounded-base border text-sm font-sans placeholder:text-paper-400 focus:outline-none focus:ring-1 disabled:opacity-50 transition-all ${error
            ? "border-error-base bg-error-light/30 focus:ring-error-base text-error-dark"
            : "border-paper-200 bg-paper-100/70 text-ink-900 focus:ring-signal-500 focus:bg-paper-50"
          } ${className}`}
        {...props}
      />
    );
  }
);

Textarea.displayName = "Textarea";
