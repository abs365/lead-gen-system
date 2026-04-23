// ------------------------------------------------------------------ //
// Shared TypeScript types — mirrors the FastAPI Pydantic schemas      //
// ------------------------------------------------------------------ //

export interface Plumber {
  id: number;
  name: string;
  address: string | null;
  postcode: string | null;
  city: string | null;
  borough: string | null;
  website: string | null;
  email: string | null;
  phone: string | null;
  lat: number | null;
  lng: number | null;
  source: string | null;
  category: string | null;
  is_commercial: number | null;
  prospect_status: string | null;
  created_at: string | null;
}

export interface DemandProspect {
  id: number;
  name: string;
  category: string | null;
  address: string | null;
  postcode: string | null;
  city: string | null;
  borough: string | null;
  website: string | null;
  email: string | null;
  phone: string | null;
  source: string | null;
  freshness_label: string | null;
  demand_score: number | null;
  fsa_rating: string | null;
  created_at: string | null;
}

export interface Match {
  id: number;
  demand_prospect_id: number;
  plumber_id: number;
  match_score: number;
  match_reason: string | null;
  created_at: string | null;
  demand_prospect: DemandProspect | null;
  plumber: Plumber | null;
}

export interface JobLog {
  id: number;
  job_type: string | null;
  status: string | null;
  message: string | null;
  records_processed: number | null;
  created_at: string | null;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  size: number;
  items: T[];
}

export interface JobResult {
  status: string;
  message: string;
  added?: number;
  skipped?: number;
  updated?: number;
}

export type ProspectStatus = 'new' | 'contacted' | 'interested' | 'client';
