/**
 * API client for the FastAPI backend.
 *
 * SECURITY:
 * - The base URL is read from NEXT_PUBLIC_API_URL (env var) with a safe default.
 * - No secrets are passed from the frontend — all sensitive ops are server-side.
 * - All fetch calls include explicit error handling.
 */

import type {
  DemandProspect,
  JobResult,
  Match,
  PaginatedResponse,
  Plumber,
} from "@/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// ------------------------------------------------------------------ //
// Generic fetch wrapper                                               //
// ------------------------------------------------------------------ //

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // ignore JSON parse failure
    }
    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}

// ------------------------------------------------------------------ //
// Collection                                                          //
// ------------------------------------------------------------------ //

export const PLUMBER_KEYWORDS = [
  "plumbers in London",
  "emergency plumbers London",
  "commercial plumbers London",
  "plumbing services London",
  "heating and plumbing London",
] as const;

export const DEMAND_CATEGORIES = [
  "all",
  "restaurant",
  "cafe",
  "takeaway",
  "pub",
  "hotel",
  "hospitality",
] as const;

export async function collectPlumbers(keyword: string): Promise<JobResult> {
  return apiFetch<JobResult>("/collect/plumbers", {
    method: "POST",
    body: JSON.stringify({ keyword, location: "London, UK" }),
  });
}

export async function collectDemand(
  category: string,
  page = 1
): Promise<JobResult> {
  return apiFetch<JobResult>("/collect/demand", {
    method: "POST",
    body: JSON.stringify({ location: "London", category, page }),
  });
}

// ------------------------------------------------------------------ //
// Enrichment                                                          //
// ------------------------------------------------------------------ //

export async function enrichPlumbers(): Promise<JobResult> {
  return apiFetch<JobResult>("/enrich/plumbers", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function enrichDemand(): Promise<JobResult> {
  return apiFetch<JobResult>("/enrich/demand", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

// ------------------------------------------------------------------ //
// Matching                                                            //
// ------------------------------------------------------------------ //

export async function runMatch(
  maxMatchesPerProspect = 3
): Promise<JobResult> {
  return apiFetch<JobResult>("/match", {
    method: "POST",
    body: JSON.stringify({
      max_matches_per_prospect: maxMatchesPerProspect,
    }),
  });
}

// ------------------------------------------------------------------ //
// Data reads                                                          //
// ------------------------------------------------------------------ //

export async function getPlumbers(params?: {
  page?: number;
  size?: number;
  search?: string;
  borough?: string;
  has_email?: boolean;
}): Promise<PaginatedResponse<Plumber>> {
  const qs = new URLSearchParams();
  if (params?.page)    qs.set("page", String(params.page));
  if (params?.size)    qs.set("size", String(params.size));
  if (params?.search)  qs.set("search", params.search);
  if (params?.borough) qs.set("borough", params.borough);
  if (params?.has_email !== undefined)
    qs.set("has_email", String(params.has_email));

  return apiFetch<PaginatedResponse<Plumber>>(
    `/plumbers${qs.toString() ? "?" + qs : ""}`
  );
}

export async function getDemandProspects(params?: {
  page?: number;
  size?: number;
  search?: string;
  category?: string;
  borough?: string;
  min_score?: number;
  has_email?: boolean;
}): Promise<PaginatedResponse<DemandProspect>> {
  const qs = new URLSearchParams();
  if (params?.page)      qs.set("page", String(params.page));
  if (params?.size)      qs.set("size", String(params.size));
  if (params?.search)    qs.set("search", params.search);
  if (params?.category)  qs.set("category", params.category);
  if (params?.borough)   qs.set("borough", params.borough);
  if (params?.min_score !== undefined)
    qs.set("min_score", String(params.min_score));
  if (params?.has_email !== undefined)
    qs.set("has_email", String(params.has_email));

  return apiFetch<PaginatedResponse<DemandProspect>>(
    `/demand${qs.toString() ? "?" + qs : ""}`
  );
}

export async function getMatches(params?: {
  page?: number;
  size?: number;
  min_score?: number;
}): Promise<PaginatedResponse<Match>> {
  const qs = new URLSearchParams();
  if (params?.page)      qs.set("page", String(params.page));
  if (params?.size)      qs.set("size", String(params.size));
  if (params?.min_score !== undefined)
    qs.set("min_score", String(params.min_score));

  return apiFetch<PaginatedResponse<Match>>(
    `/matches${qs.toString() ? "?" + qs : ""}`
  );
}

export async function updatePlumberStatus(
  id: number,
  prospect_status: string,
  notes?: string
): Promise<Plumber> {
  return apiFetch<Plumber>(`/plumbers/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ prospect_status, notes }),
  });
}

// ------------------------------------------------------------------ //
// Export URLs (direct download links — no JS fetch needed)           //
// ------------------------------------------------------------------ //
export const exportUrl = {
  plumbers: `${BASE_URL}/export/plumbers`,
  demand:   `${BASE_URL}/export/demand`,
  matches:  `${BASE_URL}/export/matches`,
};
