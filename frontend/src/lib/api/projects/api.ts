import { apiRequest } from "../client";

import type { Project } from "@/types/project";

export async function getProjects(): Promise<Project[]> {
  return apiRequest<Project[]>("/projects");
}

export async function createProject(payload: {
  name: string;
  description?: string | null;
}): Promise<Project> {
  return apiRequest<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}