import React from "react";
import { BookOpen } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  actionButtons?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionButtons,
}) => {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4">
      <div className="w-12 h-12 rounded-full bg-signal-50 border border-signal-100 flex items-center justify-center text-signal-500">
        <BookOpen className="w-6 h-6" />
      </div>
      <div className="space-y-1">
        <h3 className="font-serif text-lg font-medium text-ink-900">{title}</h3>
        <p className="text-xs font-sans text-paper-500 leading-relaxed">{description}</p>
      </div>
      {actionButtons && <div className="flex flex-wrap gap-2 justify-center pt-2">{actionButtons}</div>}
    </div>
  );
};
