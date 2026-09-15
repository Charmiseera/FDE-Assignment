export interface Session {
  session_id: string;
  title: string;
  created_at: string;
}

export interface Citation {
  source_file: string;
  episode_title: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  artifact_id: string | null;
  provider_used?: string;
  created_at: string;
}

export interface ValidationStatus {
  passed: boolean;
  word_count?: number;
  unmet_criteria: string[];
}

export interface Artifact {
  id: string;
  session_id: string;
  type: "markdown" | "html";
  title: string;
  content: string;
  metadata?: {
    validation_status?: ValidationStatus;
  };
  created_at: string;
}

export interface AppConfig {
  llm_provider: "groq" | "ollama";
  model: string;
  ollama_model: string;
  groq_model: string;
  embedding_model: string;
  groq_available: boolean;
}
