export interface PipelineStageProgress {
  name: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  input_count?: number | null;
  output_count?: number | null;
  warning_count?: number | null;
  error?: string | null;
  details?: Record<string, unknown> | null;
}

export interface StageProgress {
  current_stage: string | null;
  overall_status: string;
  stages: PipelineStageProgress[];
  updated_at: string | null;
  error?: string | null;
}

export interface ProcessingJobProgress {
  job_id: string;
  drawing_id: string;
  status: string;
  attempt_count: number;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  stage_progress: StageProgress | null;
}

export interface ProcessingJob {
  id: string;
  drawing_id: string;
  status: string;
  task_id: string | null;
  attempt_count: number;
  error_message: string | null;
  result_summary: Record<string, unknown> | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ProcessingJobListResponse {
  items: ProcessingJob[];
  total: number;
}