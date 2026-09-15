import React from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  active?: boolean;
}

export const Card: React.FC<CardProps> = ({
  active = false,
  className = "",
  children,
  ...props
}) => {
  return (
    <div
      className={`p-3 rounded-base border transition-colors ${
        active
          ? "border-signal-500 bg-signal-50 text-signal-700 shadow-2xs font-medium"
          : "border-paper-200 bg-paper-100/80 text-paper-700 hover:bg-paper-200/60 hover:text-ink-900"
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
