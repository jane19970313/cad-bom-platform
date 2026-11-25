import type { AnalysisElement, DxfAnalysisResult } from "@/types/analysis";

export type PipelineStep = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export interface CadViewerProps {
  dxfData: ArrayBuffer;
  analysis: DxfAnalysisResult;
}

export interface HandleStats {
  total: number;
  resolved: number;
  missing: number;
}

export interface StageProps {
  analysis: DxfAnalysisResult;

  selectedHandle: string | null;
  selectedElement: AnalysisElement | null;
  selectedConnectivityNode: string | null;

  selectionMessage: string;

  viewerReady: boolean;
  handleStats: HandleStats;

  search: string;
  setSearch: (value: string) => void;

  onSelectHandle: (
    handle: unknown,
    element?: AnalysisElement | null,
    shouldZoom?: boolean
  ) => void;

  onSelectNode: (handle: string) => void;
}

export const PIPELINE_STEPS = [
  { id: 1, label: "DXF Reading", short: "Reading" },
  { id: 2, label: "Entity Extraction", short: "Entities" },
  { id: 3, label: "Geometry Conversion", short: "Geometry" },
  { id: 4, label: "Spatial Indexing", short: "Spatial" },
  { id: 5, label: "Connectivity Graph", short: "Graph" },
  { id: 6, label: "Engineering Classification", short: "Classification" },
  { id: 7, label: "Relationship Serialization", short: "Relationships" },
  { id: 8, label: "Summary Generation", short: "Summary" },
] as const;