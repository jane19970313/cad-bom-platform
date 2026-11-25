export interface GeometryPoint {
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
    GeometryPoint
  )[];

  center?: GeometryPoint | null;
  radius?: number | null;

  start_angle?: number | null;
  end_angle?: number | null;

  length?: number | null;
  area?: number | null;

  warnings?: string[];
}

export interface GeometryViewProps {
  elements: GeometryElement[];
  selectedHandle: string | null;
  onSelectHandle: (handle: string) => void;
}