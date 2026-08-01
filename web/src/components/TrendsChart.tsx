import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendsResponse } from "../api";
import { sgd } from "../format";

const SPARSE_THRESHOLD = 4;

export default function TrendsChart({
  trends,
  currentEstimate,
}: {
  trends: TrendsResponse;
  currentEstimate?: number;
}) {
  const chartData: { period: string; median_price: number | null; estimate: number | null }[] =
    trends.points.map((p) => ({ ...p, estimate: null }));

  if (currentEstimate !== undefined && chartData.length > 0) {
    // Carry the last actual median into "estimate" too, so the dashed line
    // visibly connects the real trend to the model's current prediction
    // instead of the dot floating disconnected on its own.
    chartData[chartData.length - 1] = {
      ...chartData[chartData.length - 1],
      estimate: chartData[chartData.length - 1].median_price,
    };
    chartData.push({ period: "Your estimate", median_price: null, estimate: currentEstimate });
  }

  const sparse = trends.points.length < SPARSE_THRESHOLD;

  return (
    <div>
      <h3 className="mb-1 font-semibold">
        Median price history — {trends.flat_type}, {trends.town}
      </h3>
      <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        {trends.change_pct !== null && (
          <span className={trends.change_pct >= 0 ? "text-emerald-400" : "text-rose-400"}>
            {trends.change_pct >= 0 ? "+" : ""}
            {trends.change_pct}% since {trends.points[0]?.period}
          </span>
        )}
        {currentEstimate !== undefined && (
          <span className="flex items-center gap-1 text-slate-500">
            <span className="inline-block h-0.5 w-3 border-t-2 border-dashed border-amber-400" />
            your estimate vs. the trend
          </span>
        )}
      </div>
      {sparse && (
        <p className="mb-3 text-xs text-amber-400">
          Only {trends.points.length} quarter{trends.points.length === 1 ? "" : "s"} of data for
          this town + flat type combination — treat this trend as directional, not precise.
        </p>
      )}
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ left: 20, right: 20 }}>
          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
          <XAxis dataKey="period" stroke="#64748b" fontSize={11} minTickGap={40} />
          <YAxis
            tickFormatter={(v: number) => `$${Math.round(v / 1000)}k`}
            stroke="#64748b"
            fontSize={12}
            width={55}
            domain={["auto", "auto"]}
          />
          <Tooltip
            formatter={(v, name) => [
              sgd(Number(v)),
              name === "estimate" ? "Your estimate" : "Median price",
            ]}
            contentStyle={{
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: 8,
            }}
          />
          <Line
            type="monotone"
            dataKey="median_price"
            stroke="#34d399"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="estimate"
            stroke="#fbbf24"
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={{ r: 4, fill: "#fbbf24", strokeWidth: 0 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
