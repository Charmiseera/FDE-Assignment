import React from "react";
import { AlertCircle, AlertTriangle, CheckCircle, Info } from "lucide-react";

interface AlertProps {
  variant?: "warning" | "error" | "info" | "success";
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  variant = "info",
  title,
  children,
  className = "",
}) => {
  const styles = {
    warning: "bg-warning-light border-warning-base text-warning-dark",
    error: "bg-error-light border-error-base text-error-dark",
    info: "bg-info-light border-info-base text-info-dark",
    success: "bg-success-light border-success-base text-success-dark",
  };

  const icons = {
    warning: <AlertTriangle className="w-5 h-5 text-warning-base shrink-0 mt-0.5" />,
    error: <AlertCircle className="w-5 h-5 text-error-base shrink-0 mt-0.5" />,
    info: <Info className="w-5 h-5 text-info-base shrink-0 mt-0.5" />,
    success: <CheckCircle className="w-5 h-5 text-success-base shrink-0 mt-0.5" />,
  };

  return (
    <div
      role="alert"
      className={`flex gap-3 p-3.5 rounded-base border text-sm ${styles[variant]} ${className}`}
    >
      {icons[variant]}
      <div className="flex-1">
        {title && <h4 className="font-medium mb-1">{title}</h4>}
        <div className="text-xs leading-relaxed">{children}</div>
      </div>
    </div>
  );
};
