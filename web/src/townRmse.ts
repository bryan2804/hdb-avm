export type RmseTier = "precise" | "typical" | "wide";

export interface TownRmseRank {
  tier: RmseTier;
  rank: number; // 1 = most precise town in the model
  total: number;
  percentile: number; // 0 = most precise, 100 = widest
}

/** Ranks a town's RMSE against every other town the model covers, computed
 * live from the served metrics artifact — no tier thresholds are hardcoded
 * against a specific model generation, they move with each retrain. */
export function rankTownRmse(
  townRmse: Record<string, number>,
  town: string,
): TownRmseRank | null {
  const entries = Object.entries(townRmse).sort((a, b) => a[1] - b[1]);
  const idx = entries.findIndex(([t]) => t === town);
  if (idx === -1 || entries.length < 2) return null;

  const total = entries.length;
  const percentile = Math.round((idx / (total - 1)) * 100);
  const tier: RmseTier = percentile < 33 ? "precise" : percentile < 67 ? "typical" : "wide";
  return { tier, rank: idx + 1, total, percentile };
}

export const TIER_COPY: Record<RmseTier, string> = {
  precise: "one of the model's most precise towns — a more uniform mix of similar-vintage flats.",
  typical: "typical precision for this model.",
  wide: "one of the model's least precise towns — mature estates like this mix flats from very different eras, floor levels, and renovation states, which is inherently harder to price than a newer, uniform town.",
};

export const TIER_STYLE: Record<RmseTier, string> = {
  precise: "border-emerald-900 bg-emerald-950/30 text-emerald-300",
  typical: "border-slate-800 bg-slate-900/60 text-slate-300",
  wide: "border-amber-900 bg-amber-950/40 text-amber-300",
};
