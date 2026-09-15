import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Session, Message, Artifact, AppConfig } from "./types";
import { SessionSidebar } from "./components/sidebar/SessionSidebar";
import { Header } from "./components/header/Header";
import { ChatPanel } from "./components/chat/ChatPanel";
import { ArtifactViewer } from "./components/artifacts/ArtifactViewer";

const API_BASE = "http://localhost:8000/api/v1";

export function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  // Provider selected by the user — starts as backend default, can be toggled per session
  const [activeProvider, setActiveProvider] = useState<"ollama" | "groq">("ollama");
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetchConfig();
    fetchSessions();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await axios.get(`${API_BASE}/config`);
      if (res.data.success) {
        const cfg: AppConfig = res.data.data;
        setConfig(cfg);
        setActiveProvider(cfg.llm_provider);
      }
    } catch (e) {
      console.error("Failed to load config:", e);
    }
  };

  const fetchSessions = async () => {
    try {
      const res = await axios.get(`${API_BASE}/sessions`);
      if (res.data.success) {
        const sessionList = res.data.data;
        setSessions(sessionList);
        if (sessionList.length > 0 && !activeSessionId) {
          selectSession(sessionList[0].session_id);
        }
      }
    } catch (e) {
      console.error("Failed to load sessions:", e);
    }
  };

  const selectSession = async (sessionId: string) => {
    setActiveSessionId(sessionId);
    setActiveArtifact(null);
    try {
      const res = await axios.get(`${API_BASE}/sessions/${sessionId}/messages`);
      if (res.data.success) {
        setMessages(res.data.data);
      }
    } catch (e) {
      console.error("Failed to load messages:", e);
    }
  };

  const handleNewChat = async () => {
    try {
      setIsLoading(true);
      const res = await axios.post(`${API_BASE}/sessions`, {});
      if (res.data.success) {
        const newSessionId = res.data.data.session_id;
        setActiveSessionId(newSessionId);
        setMessages([]);
        setActiveArtifact(null);
        await fetchSessions();
      }
    } catch (e) {
      console.error("Failed to create session:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (content: string) => {
    let currentSessionId = activeSessionId;

    if (!currentSessionId) {
      try {
        const sRes = await axios.post(`${API_BASE}/sessions`, {});
        currentSessionId = sRes.data.data.session_id;
        setActiveSessionId(currentSessionId);
      } catch (e) {
        console.error("Failed to create initial session:", e);
        return;
      }
    }

    const tempUserMsg: Message = {
      id: "temp-" + Date.now(),
      role: "user",
      content,
      citations: [],
      artifact_id: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await axios.post(
        `${API_BASE}/sessions/${currentSessionId}/messages`,
        {
          content,
          provider: activeProvider, // send selected provider override with every request
        },
        {
          signal: controller.signal,
        }
      );

      if (res.data.success) {
        const assistantData = res.data.data;
        const assistantMsg: Message = {
          id: assistantData.message_id,
          role: "assistant",
          content: assistantData.content,
          citations: assistantData.citations,
          artifact_id: assistantData.artifact_id,
          provider_used: assistantData.provider_used,
          created_at: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMsg]);

        if (assistantData.artifact_id) {
          handleOpenArtifact(assistantData.artifact_id, currentSessionId);
        }

        fetchSessions();
      }
    } catch (e: any) {
      if (axios.isCancel(e) || e.name === "CanceledError" || e.code === "ERR_CANCELED") {
        console.log("Message generation cancelled by user");
        const stoppedMsg: Message = {
          id: "stopped-" + Date.now(),
          role: "assistant",
          content: "*(Generation stopped by user)*",
          citations: [],
          artifact_id: null,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, stoppedMsg]);
      } else {
        console.error("Failed to send message:", e);
      }
    } finally {
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  };

  const handleOpenArtifact = async (artifactId: string, sessionId?: string | null) => {
    if (!artifactId) return;
    const sId = sessionId || activeSessionId || "00000000-0000-0000-0000-000000000000";

    try {
      const res = await axios.get(`${API_BASE}/sessions/${sId}/artifacts/${artifactId}`);
      if (res.data.success) {
        setActiveArtifact(res.data.data);
      }
    } catch (e) {
      console.error("Failed to fetch artifact:", e);
    }
  };


  return (
    <div className="flex h-screen w-screen bg-paper-50 font-sans overflow-hidden">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={selectSession}
        onNewChat={handleNewChat}
        isLoading={isLoading}
      />

      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <Header
          config={config}
          activeProvider={activeProvider}
          onToggleProvider={setActiveProvider}
        />

        <div className="flex-1 flex h-[calc(100vh-3.5rem)] overflow-hidden">
          <div className="flex-1 h-full min-w-0">
            <ChatPanel
              messages={messages}
              onSendMessage={handleSendMessage}
              onOpenArtifact={handleOpenArtifact}
              onStopGeneration={handleStopGeneration}
              isLoading={isLoading}
            />
          </div>

          {activeArtifact && (
            <div className="w-[45%] h-full min-w-[360px] animate-in slide-in-from-right duration-200">
              <ArtifactViewer
                artifact={activeArtifact}
                onClose={() => setActiveArtifact(null)}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
