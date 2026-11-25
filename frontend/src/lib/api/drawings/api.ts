import {
  apiRequest,
  ApiError,
  API_BASE_URL,
} from "../client";

import {
  clearAccessToken,
  getAccessToken,
} from "@/lib/auth";

import type {
  Drawing,
  DrawingListResponse,
} from "@/types/drawing";

export async function getProjectDrawings(
  projectId: string,
): Promise<DrawingListResponse> {
  return apiRequest<DrawingListResponse>(
    `/drawings/drawings/projects/${encodeURIComponent(projectId)}`,
  );
}

export async function uploadDrawing(
  projectId: string,
  file: File,
): Promise<Drawing> {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<Drawing>(
    `/drawings/drawings/projects/${encodeURIComponent(projectId)}/upload`,
    {
      method: "POST",
      body: formData,
    },
  );
}

export async function getDrawing(drawingId: string): Promise<Drawing> {
  return apiRequest<Drawing>(
    `/drawings/drawings/${encodeURIComponent(drawingId)}`
  );
}

export async function downloadDrawingDxf(
  drawingId: string
): Promise<ArrayBuffer> {
  const token = getAccessToken();

  const response = await fetch(
    `${API_BASE_URL}/drawings/drawings/${encodeURIComponent(drawingId)}/download`,
    {
      method: "GET",
      headers: {
        Accept: "application/dxf, application/octet-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  if (!response.ok) {
    if (response.status === 401) {
      clearAccessToken();
    }

    const message = await response.text().catch(() => "");
    throw new ApiError(
      message || `DXF download failed with status ${response.status}`,
      response.status
    );
  }

  return response.arrayBuffer();
}