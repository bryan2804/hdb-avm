/** Typed client for the HDB AVM API. */

const BASE = import.meta.env.VITE_API_URL ?? "";

export interface Metadata {
  towns: string[];
  flat_types: string[];
  model_version: string;
  trained_at: string | null;
  rmse: number;
  r2: number | null;
}

export interface ValuationRequest {
  town: string;
  flat_type: string;
  floor_area_sqm: number;
  storey: number;
  remaining_lease_years: number;
  address?: string;
  latitude?: number;
  longitude?: number;
  mrt_distance_km?: number;
}

export interface Contribution {
  feature: string;
  label: string;
  amount: number;
}

export interface ValuationResponse {
  point_estimate: number;
  band_low: number;
  band_high: number;
  rmse: number;
  rmse_scope: "town" | "global";
  mispricing_exposure_pct: number;
  valuation_date: string;
  resolved_location: {
    coordinate_source: "address" | "explicit" | "town_centroid";
    latitude: number;
    longitude: number;
    mrt_distance_km: number;
    nearest_mrt: string | null;
    matched_address: string | null;
  };
  explanation: {
    baseline: number;
    contributions: Contribution[];
  };
}

export interface TrendsResponse {
  town: string;
  flat_type: string;
  points: { period: string; median_price: number }[];
  change_pct: number | null;
}

export interface MetricsArtifact {
  default_rmse: number;
  town_rmse: Record<string, number>;
}

export interface MarketMover {
  town: string;
  median_price: number;
  yoy_change_pct: number;
}

export interface MarketMoversResponse {
  flat_type: string;
  movers: MarketMover[];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    detail: string,
  ) {
    super(detail);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, init);
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body — keep statusText */
    }
    throw new ApiError(resp.status, detail);
  }
  return resp.json() as Promise<T>;
}

export const getMetadata = () => request<Metadata>("/api/v1/metadata");

export const createValuation = (body: ValuationRequest) =>
  request<ValuationResponse>("/api/v1/valuations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const getTrends = (town: string, flatType: string) =>
  request<TrendsResponse>(
    `/api/v1/trends?town=${encodeURIComponent(town)}&flat_type=${encodeURIComponent(flatType)}`,
  );

export const getMetrics = () => request<MetricsArtifact>("/api/v1/metrics");

export const getMarketMovers = (flatType: string) =>
  request<MarketMoversResponse>(`/api/v1/market-movers?flat_type=${encodeURIComponent(flatType)}`);
