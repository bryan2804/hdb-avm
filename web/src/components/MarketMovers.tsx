import type { MarketMoversResponse } from "../api";

function Row({ town, pct }: { town: string; pct: number }) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="text-slate-300">{town}</span>
      <span className={pct >= 0 ? "text-emerald-400" : "text-rose-400"}>
        {pct >= 0 ? "+" : ""}
        {pct}%
      </span>
    </div>
  );
}

export default function MarketMovers({ data }: { data: MarketMoversResponse }) {
  if (data.movers.length < 2) {
    return (
      <div>
        <h3 className="mb-1 font-semibold">Market movers — {data.flat_type}</h3>
        <p className="text-sm text-slate-500">
          Not enough towns with year-over-year history for this flat type yet.
        </p>
      </div>
    );
  }

  const sorted = [...data.movers].sort((a, b) => b.yoy_change_pct - a.yoy_change_pct);
  // Cap each side at half the list so a data-sparse flat type (few towns
  // with a prior-year comparison) never shows the same town in both columns.
  const perSide = Math.min(5, Math.floor(sorted.length / 2));
  const rising = sorted.slice(0, perSide);
  const falling = sorted.slice(-perSide).reverse();

  return (
    <div>
      <h3 className="mb-1 font-semibold">Market movers — {data.flat_type}</h3>
      <p className="mb-3 text-xs text-slate-500">
        Year-over-year median price change by town — a lender's view of which collateral is
        appreciating vs. depreciating.
      </p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="mb-1 text-xs font-medium text-slate-500">Rising fastest</div>
          {rising.map((m) => (
            <Row key={m.town} town={m.town} pct={m.yoy_change_pct} />
          ))}
        </div>
        <div>
          <div className="mb-1 text-xs font-medium text-slate-500">Falling fastest</div>
          {falling.map((m) => (
            <Row key={m.town} town={m.town} pct={m.yoy_change_pct} />
          ))}
        </div>
      </div>
    </div>
  );
}
