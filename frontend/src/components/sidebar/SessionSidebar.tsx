import React from "react";
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { Session } from "../../types";
import { Button } from "../ui/Button";

interface SessionSidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession?: (id: string) => void;
  isLoading: boolean;
}

export const SessionSidebar: React.FC<SessionSidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  isLoading,
}) => {
  return (
    <aside className="w-64 h-full flex flex-col bg-paper-100 border-r border-paper-200">
      {/* Brand & New Chat Button */}
      <div className="p-4 border-b border-paper-200 space-y-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-base bg-ink-700 flex items-center justify-center text-paper-50 font-sans font-bold text-xs shadow-2xs">
            L
          </div>
          <div className="flex flex-col">
            <span className="font-sans font-semibold text-sm text-ink-900 leading-tight">
              Lenny Growth
            </span>
            <span className="font-sans text-[10px] text-paper-500 font-medium">
              Operator's Workbench
            </span>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2 bg-paper-50 hover:bg-paper-100 border-paper-300 text-ink-800 font-medium shadow-2xs transition-all"
          onClick={onNewChat}
          disabled={isLoading}
        >
          <Plus className="w-4 h-4 text-signal-500" />
          <span>New Chat</span>
        </Button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="px-2 pb-1.5 flex items-center justify-between">
          <span className="text-[10px] font-sans font-semibold text-paper-500 uppercase tracking-wider">
            Conversations
          </span>
          <span className="text-[10px] font-mono text-paper-400">
            {sessions.length}
          </span>
        </div>

        {sessions.length === 0 ? (
          <div className="px-3 py-8 text-center text-xs text-paper-400 font-sans leading-relaxed">
            No active conversations.<br />Start a new chat to begin.
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.session_id === activeSessionId;
            return (
              <div
                key={session.session_id}
                className={`group relative flex items-center rounded-base border transition-all ${isActive
                    ? "border-signal-500 bg-signal-50 text-signal-700 font-medium shadow-2xs"
                    : "border-transparent text-paper-700 hover:bg-paper-200/60 hover:text-ink-900"
                  }`}
              >
                <button
                  onClick={() => onSelectSession(session.session_id)}
                  className="w-full text-left p-2.5 text-xs font-sans flex items-start gap-2.5 truncate"
                >
                  <MessageSquare
                    className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${isActive ? "text-signal-500" : "text-paper-400 group-hover:text-ink-700"
                      }`}
                  />
                  <span className="truncate flex-1 font-sans">
                    {session.title || "Untitled Session"}
                  </span>
                </button>

                {onDeleteSession && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.session_id);
                    }}
                    title="Delete conversation"
                    className="opacity-0 group-hover:opacity-100 p-1.5 mr-1 rounded-sm text-paper-400 hover:text-error-base hover:bg-error-light/50 transition-all"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};

