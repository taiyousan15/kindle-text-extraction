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

export interface Stats {
  totalJobs: number;
  completedJobs: number;
  processingJobs: number;
  failedJobs: number;
  totalPages: number;
  successRate: number;
}
