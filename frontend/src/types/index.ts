// ---- 数据模型 ----

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources: SourceInfo[];
  createdAt: string;
}

export interface SourceInfo {
  file_id: number;
  title: string;
  department: string;
  date: string;
  snippet: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
}

export interface DocumentSource {
  id: string;
  file_id: number;
  title: string;
  department: string;
  date: string;
  status: string;
  chunk_count: number;
  indexed_at: string | null;
  created_at: string;
}

export interface SystemStats {
  total_sources: number;
  indexed_sources: number;
  total_chunks: number;
  error_sources: number;
}
