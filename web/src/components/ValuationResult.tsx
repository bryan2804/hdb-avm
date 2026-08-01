import type { ValuationResponse } from "../api";
import { sgd } from "../format";
import { rankTownRmse, TIER_COPY, TIER_STYLE } from "../townRmse";

const SOURCE_LABELS: Record<string, string> = {
  address: "block-level (geocoded address)",
  explicit: "exact coordinates",
  town_centroid: "town centroid",
};

export default function ValuationResult({
  valuation,
  town,
  townRmse,
}: {
  valuation: ValuationResponse;
  town: string | null;
  townRmse: Record<string, number> | null;
}) {
  const loc = valuation.resolved_location;
  const rank = town && townRmse ? rankTownRmse(townRmse, town) : null;
  return (
    <div className="space-y-4">
      <div>
        <div className="text-sm text-slate-400">Estimated resale price</div>
        <div className="text-4xl font-bold tracking-tight text-emerald-400">
          {sgd(valuation.point_estimate)}
        </div>
        <div className="mt-1 text-sm text-slate-300">
          {sgd(valuation.band_low)} – {sgd(valuation.band_high)}{" "}
          <span className="text-slate-500">
            (±{sgd(valuation.rmse)} {valuation.rmse_scope === "town" ? "town-level" : "global"} RMSE)
          </span>
        </div>
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-sm text-slate-300">
        Model uncertainty represents{" "}
        <span className="font-semibold text-slate-100">
          {valuation.mispricing_exposure_pct}% collateral mispricing exposure
        </span>{" "}
        for a mortgage lender on this flat.
      </div>

      {rank && town && (
        <div className={`rounded-lg border p-3 text-sm ${TIER_STYLE[rank.tier]}`}>
          <span className="font-semibold">
            {town} ranks #{rank.rank} of {rank.total} towns by pricing precision
          </span>{" "}
          ({rank.percentile}th percentile widest) — {TIER_COPY[rank.tier]}
        </div>
      )}

      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <dt className="text-slate-500">Location precision</dt>
        <dd>{SOURCE_LABELS[loc.coordinate_source] ?? loc.coordinate_source}</dd>
        {loc.matched_address && (
          <>
            <dt className="text-slate-500">Matched address</dt>
            <dd>{loc.matched_address}</dd>
          </>
        )}
        {loc.nearest_mrt && (
          <>
            <dt className="text-slate-500">Nearest MRT</dt>
            <dd>
              {loc.nearest_mrt} ({loc.mrt_distance_km.toFixed(2)} km)
            </dd>
          </>
        )}
        <dt className="text-slate-500">Valuation date</dt>
        <dd>{valuation.valuation_date}</dd>
      </dl>
    </div>
  );
}
