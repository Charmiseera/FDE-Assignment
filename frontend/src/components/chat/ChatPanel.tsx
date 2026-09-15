import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Sparkles, BookOpen, FileText, ArrowRight } from "lucide-react";
import { Message } from "../../types";
import { Button } from "../ui/Button";
import { Textarea } from "../ui/Textarea";
import { LoadingDots } from "../ui/LoadingDots";

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  onOpenArtifact: (artifactId: string) => void;
  isLoading: boolean;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  onSendMessage,
  onOpenArtifact,
  isLoading,
}) => {
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleTriggerShip30 = () => {
    onSendMessage("Please turn our grounded discussion into a Ship 30/30 essay based on the verified transcript context.");
  };

  return (
    <div className="flex flex-col h-full bg-paper-50">
      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto space-y-5">
            <div className="w-12 h-12 rounded-full bg-signal-50 border border-signal-100 flex items-center justify-center text-signal-500 shadow-2xs">
              <BookOpen className="w-6 h-6" />
            </div>
            <div className="space-y-1.5">
              <h3 className="font-sans font-semibold text-lg text-ink-900 tracking-tight">
                Grounded Growth & Product Knowledge
              </h3>
              <p className="text-xs font-sans text-paper-600 leading-relaxed max-w-md">
                Ask tactical questions sourced strictly from verified transcripts, then transform insights directly into publish-ready Ship 30/30 essays and HTML artifacts.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row flex-wrap gap-2 justify-center pt-2">
              <button
                onClick={() => onSendMessage("How do top PLG companies define product activation milestones?")}
                className="text-xs font-sans text-paper-700 bg-paper-100 hover:bg-paper-200/80 px-3.5 py-2 rounded-base border border-paper-200 transition-all text-left flex items-center justify-between gap-2 group"
              >
                <span>"How do PLG leaders define activation?"</span>
                <ArrowRight className="w-3 h-3 text-paper-400 group-hover:text-signal-500 transition-colors" />
              </button>
              <button
                onClick={() => onSendMessage("What is Elena Verna's advice on B2B product-led growth?")}
                className="text-xs font-sans text-paper-700 bg-paper-100 hover:bg-paper-200/80 px-3.5 py-2 rounded-base border border-paper-200 transition-all text-left flex items-center justify-between gap-2 group"
              >
                <span>"What is Elena Verna's advice on B2B PLG?"</span>
                <ArrowRight className="w-3 h-3 text-paper-400 group-hover:text-signal-500 transition-colors" />
              </button>
            </div>
          </div>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-4 font-sans text-sm ${m.role === "user"
                    ? "bg-ink-700 text-paper-50 font-normal leading-relaxed shadow-2xs"
                    : "bg-paper-100/90 text-paper-900 border border-paper-200 shadow-2xs space-y-3"
                  }`}
              >
                {m.role === "assistant" ? (
                  <div className="prose font-sans text-sm text-paper-900 space-y-2 leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{m.content}</p>
                )}


                {/* Citations */}
                {m.citations && m.citations.length > 0 && (
                  <div className="pt-2 border-t border-paper-200 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[11px] font-sans text-paper-500 font-medium">Sources:</span>
                    {m.citations.map((c, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-signal-50 text-signal-700 border border-signal-100 font-mono text-[10px]"
                      >
                        {c.episode_title || c.source_file}
                      </span>
                    ))}
                  </div>
                )}

                {/* View Artifact Button */}
                {m.artifact_id && (
                  <div className="pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onOpenArtifact(m.artifact_id!)}
                      className="text-xs gap-1.5 border-signal-500/40 text-signal-700 bg-signal-50 hover:bg-signal-100 shadow-2xs"
                    >
                      <FileText className="w-3.5 h-3.5 text-signal-500" />
                      View Generated Artifact
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="flex items-center gap-2 p-2">
            <LoadingDots label="Consulting transcripts and generating response..." />
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-paper-200 bg-paper-50 space-y-2">
        {/* Quick action bar */}
        <div className="flex items-center justify-between">
          <button
            onClick={handleTriggerShip30}
            disabled={isLoading || messages.length === 0}
            className="inline-flex items-center gap-1.5 text-xs font-sans font-medium text-signal-700 hover:text-signal-700/80 disabled:opacity-40 disabled:pointer-events-none transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-signal-500" />
            <span>Generate Ship 30/30 Essay</span>
          </button>
          <span className="text-[11px] text-paper-400 font-sans">
            Shift + Enter for new line
          </span>
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2 items-end">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Ask a product question, request analysis, or generate an essay..."
            rows={2}
            className="flex-1 text-sm font-sans"
          />
          <Button
            type="submit"
            variant="primary"
            disabled={!input.trim() || isLoading}
            className="h-10 px-4 gap-1.5 shrink-0"
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
};
