import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
}

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...props
}) => {
  const base = "inline-flex items-center justify-center font-sans font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-500 disabled:opacity-50 disabled:pointer-events-none rounded-base";

  const variants = {
    primary: "bg-ink-700 hover:bg-ink-600 active:bg-ink-800 text-paper-50 shadow-sm",
    outline: "border border-paper-200 bg-paper-50 hover:bg-paper-100 text-ink-700",
    ghost: "hover:bg-paper-100 text-ink-700",
    danger: "bg-error-base hover:bg-error-dark text-paper-50",
  };

  const sizes = {
    sm: "h-8 px-3 text-xs",
    md: "h-9 px-4 text-sm",
    lg: "h-11 px-6 text-base",
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};
