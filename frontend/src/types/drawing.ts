export interface Drawing {
  id: string;
  project_id: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  checksum_sha256: string;
  status: string;
  created_at: string;
}

export interface DrawingListResponse {
  items: Drawing[];
  total: number;
}