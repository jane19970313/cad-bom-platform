import { apiRequest } from "../client";

import type {
  ProcessingJob,
  ProcessingJobListResponse,
  ProcessingJobProgress,
} from "@/types/processing";

export async function submitDrawingProcessing(
  drawingId: string,
): Promise<ProcessingJob> {
  return apiRequest<ProcessingJob>(
    `/processing/drawings/${encodeURIComponent(drawingId)}/process`,
    {
      method: "POST",
    },
  );
}

export async function getDrawingJobs(
  drawingId: string,
): Promise<ProcessingJobListResponse> {
  return apiRequest<ProcessingJobListResponse>(
    `/processing/drawings/${encodeURIComponent(drawingId)}/jobs`,
  );
}

export async function getProcessingJobProgress(
  jobId: string,
): Promise<ProcessingJobProgress> {
  return apiRequest<ProcessingJobProgress>(
    `/processing/jobs/${encodeURIComponent(jobId)}/progress`,
  );
}