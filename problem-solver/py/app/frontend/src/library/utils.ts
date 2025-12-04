import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import axios, { AxiosInstance } from "axios";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type AgentStatus = "question" | "complete" | "processing" | "error";

export type TaskCategory = "informational" | "build_model" | "unclear";

export type ChatMode = "auto" | "consultant" | "designer";

export interface FormField {
  name: string;
  label: string;
  description?: string | null;
  placeholder?: string | null;
  value?: string | null;
  required: boolean;
}

interface ChatPayload {
  query: string;
  session_id?: string;
  user_response?: string;
  form_data?: Record<string, string>;
  chat_mode?: ChatMode;
}

export interface ChatResponse {
  status: AgentStatus;
  message: string;
  session_id: string;
  category?: TaskCategory;
  collected_data?: Record<string, string>;
  form_fields?: FormField[] | null;
  recommended_model?: string | null;
  confidence?: number | null;
  reasoning?: string | null;
  alternative_models?: string[] | null;
  best_link?: string | null;
  other_links?: string[];
}

interface FileUploadResponse {
  message: string;
  file_id: number;
  filename: string;
}

interface FileDeleteResponse {
  success: boolean;
  message: string;
}

export interface DocumentsInfo {
  id: number;
  filename: string;
  upload_timestamp: string;
}

interface DocumentDeleteRequest {
  file_id: number;
}

export interface DialogInfo {
  session_id: string;
  title?: string | null;
  category?: TaskCategory | null;
  chat_mode?: string | null;
  last_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DialogMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  category?: TaskCategory | null;
  meta?: Record<string, unknown> | null;
}

const API_BASE_URL = import.meta.env.VITE_UNIFIED_API_URL ?? "http://localhost:8000";

const API: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
});

export const api = {
  async chat(payload: ChatPayload): Promise<ChatResponse> {
    const { data } = await API.post<ChatResponse>("/api/v1/chat", payload);
    return data;
  },

  async uploadDoc(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const { data } = await API.post<FileUploadResponse>(
      "/api/v1/documents/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      },
    );
    return data;
  },

  async deleteDoc(fileId: number): Promise<FileDeleteResponse> {
    const payload: DocumentDeleteRequest = { file_id: fileId };
    const { data } = await API.delete<FileDeleteResponse>("/api/v1/documents/delete", {
      data: payload,
      headers: { "Content-Type": "application/json" },
    });
    return data;
  },

  async getFileList(): Promise<DocumentsInfo[]> {
    const { data } = await API.get<DocumentsInfo[]>("/api/v1/documents/list");
    return data;
  },

  async listDialogs(): Promise<DialogInfo[]> {
    const { data } = await API.get<DialogInfo[]>("/api/v1/dialogs");
    return data;
  },

  async createDialog(title?: string, chatMode?: ChatMode): Promise<DialogInfo> {
    const { data } = await API.post<DialogInfo>("/api/v1/dialogs", { title, chat_mode: chatMode });
    return data;
  },

  async getDialogMessages(sessionId: string): Promise<DialogMessage[]> {
    const { data } = await API.get<DialogMessage[]>(`/api/v1/dialogs/${sessionId}/messages`);
    return data;
  },

  async deleteDialog(sessionId: string): Promise<{ success: boolean; message: string }> {
    const { data } = await API.delete<{ success: boolean; message: string }>(`/api/v1/dialogs/${sessionId}`);
    return data;
  },
};