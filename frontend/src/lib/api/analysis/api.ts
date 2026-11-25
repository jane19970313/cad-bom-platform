import { apiRequest } from "../client";

import type {
  AnalysisResult,
  DxfAnalysisResult,
} from "@/types/analysis";

export async function getAnalysisResult(
  jobId: string
): Promise<DxfAnalysisResult> {
  return apiRequest<DxfAnalysisResult>(
    `/analysis/jobs/${encodeURIComponent(jobId)}/result`
  );
}