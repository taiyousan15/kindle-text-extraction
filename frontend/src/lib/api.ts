import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error("API Error:", error.response.data);
    } else if (error.request) {
      console.error("Network Error:", error.request);
    } else {
      console.error("Error:", error.message);
    }
    return Promise.reject(error);
  }
);

export interface HealthCheck {
  status: string;
  database: string;
  pool_size: number;
}

export interface Job {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  pages_captured: number;
  book_title?: string;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface OCRResult {
  job_id: string;
  text: string;
  confidence: number;
  page_num: number;
}

export interface CaptureRequest {
  email: string;
  password: string;
  book_url: string;
  book_title: string;
  max_pages: number;
  headless: boolean;
}

export interface RAGRequest {
  question: string;
  book_title?: string;
  top_k?: number;
}

export interface RAGResponse {
  answer: string;
  sources: Array<{
    text: string;
    page_num: number;
    confidence: number;
  }>;
}

// API Functions
export const api = {
  // Health Check
  health: async (): Promise<HealthCheck> => {
    const response = await apiClient.get("/health");
    return response.data;
  },

  // OCR
  uploadImage: async (file: File, bookTitle: string, pageNum: number): Promise<OCRResult> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("book_title", bookTitle);
    formData.append("page_num", pageNum.toString());

    const response = await apiClient.post("/api/v1/ocr/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  // Capture
  startCapture: async (data: CaptureRequest): Promise<{ job_id: string }> => {
    const response = await apiClient.post("/api/v1/capture/start", data);
    return response.data;
  },

  stopCapture: async (jobId: string): Promise<void> => {
    await apiClient.post(`/api/v1/capture/stop/${jobId}`);
  },

  // Jobs
  getJob: async (jobId: string): Promise<Job> => {
    const response = await apiClient.get(`/api/v1/ocr/job/${jobId}`);
    return response.data;
  },

  listJobs: async (limit: number = 10): Promise<Job[]> => {
    const response = await apiClient.get("/api/v1/ocr/jobs", {
      params: { limit },
    });
    return response.data;
  },

  // RAG
  askQuestion: async (data: RAGRequest): Promise<RAGResponse> => {
    const response = await apiClient.post("/api/v1/rag/ask", data);
    return response.data;
  },

  // Knowledge Extraction
  extractKnowledge: async (bookTitle: string): Promise<any> => {
    const response = await apiClient.post("/api/v1/knowledge/extract", {
      book_title: bookTitle,
    });
    return response.data;
  },

  listKnowledge: async (): Promise<any[]> => {
    const response = await apiClient.get("/api/v1/knowledge/list");
    return response.data;
  },
};
