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

export default function TrendsChart({ trends }: { trends: TrendsResponse }) {
  return (
    <div>
      <h3 className="mb-1 font-semibold">
        Median price history — {trends.flat_type}, {trends.town}
      </h3>
      {trends.change_pct !== null && (
        <p className="mb-3 text-sm text-slate-400">
          {trends.change_pct >= 0 ? "+" : ""}
          {trends.change_pct}% since {trends.points[0]?.period}
        </p>
      )}
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={trends.points} margin={{ left: 20, right: 20 }}>
          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
          <XAxis dataKey="period" stroke="#64748b" fontSize={11} minTickGap={40} />
          <YAxis
            tickFormatter={(v: number) => `$${Math.round(v / 1000)}k`}
            stroke="#64748b"
            fontSize={12}
            width={55}
          />
          <Tooltip
            formatter={(v) => [sgd(Number(v)), "Median price"]}
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
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
