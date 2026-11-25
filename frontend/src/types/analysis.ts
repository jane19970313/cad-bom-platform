
export interface RawEntitySource {
  entity_handle: string;
  entity_type: string;
  layer: string | null;
  layout: string | null;
  block_path: string[];
}
export interface RawEntity {
  source: RawEntitySource;

  attributes: Record<string, unknown>;

  text: string | null;

  warnings: string[];
}
export interface GeometryPoint3D {
  x: number;
  y: number;
  z?: number;
}

export interface GeometryElement {
  element_id: string;
  source_handle: string;

  source_type?: string;
  layer?: string;
  layout?: string;
  block_path?: string[];

  geometry_type: string;
  caption: string;

  is_closed: boolean;
  is_valid: boolean;

  coordinates_3d: (
    [number, number, number] |
    GeometryPoint3D
  )[];

  center?: GeometryPoint3D | null;
  radius?: number | null;

  start_angle?: number | null;
  end_angle?: number | null;

  length?: number | null;
  area?: number | null;

  warnings?: string[];
}
export interface AnalysisElement {
  id?: string;
  handle?: string;
  source_handle?: string;
  entity_type?: string;
  dxf_type?: string;
  layer?: string;
  geometry_type?: string;
  engineering_type?: string;
  classification?: string;
  status?: string;
  confidence?: number;
  length?: number;
  coordinates_3d?: number[][];
  nearby_element_count?: number;
  [key: string]: unknown;
}

export interface AnalysisResult {
  engine_version?: string;
  drawing?: Record<string, unknown>;
  summary?: Record<string, unknown>;
  raw_entities?: Record<string, unknown>[];
  elements?: AnalysisElement[];
  relationships?: Record<string, unknown>[];
  diagnostics?: Record<string, unknown>[];
  [key: string]: unknown;
}

export interface BomElement {
  caption: string;

  length: number | null;
  area: number | null;
  count: number;

  material: string | null;

  volume: number | null;
  mass: number | null;

  source_handles: string[];
}

export interface DxfAnalysisResult {
  engine_version: string;

  drawing: {
    path: string;
    version: string;
    units_code: number;
    units_name: string;
    warnings: string[];
  };

  settings: {
    flattening_distance: number;
    connectivity_tolerance: number;
    nearby_distance: number;
  };

  summary: {
    raw_entity_count: number;
    geometry_element_count: number;
    classified_element_count: number;
    bom_element_count: number;
    geometry_conversion_failure_count: number;
    connectivity_node_count: number;
    connectivity_edge_count: number;
  };

  raw_entities: RawEntity[];
  geometry_elements?: GeometryElement[];
  elements: AnalysisElement[];
  bom_elements?: BomElement[];
  relationships: any[];
  diagnostics: any[];

  connectivity_nodes?: any[];

  spatial_index?: {
    indexed_element_count: number;
  };
}