import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ValuationResponse } from "../api";
import { sgd, signedSgd } from "../format";

export default function ContributionsChart({ valuation }: { valuation: ValuationResponse }) {
  const data = valuation.explanation.contributions.map((c) => ({
    label: c.label,
    amount: c.amount,
  }));

  return (
    <div>
      <h3 className="mb-1 font-semibold">Why this price?</h3>
      <p className="mb-3 text-sm text-slate-400">
        Starting from the average flat ({sgd(valuation.explanation.baseline)}), each factor
        pushes the estimate up or down (exact TreeSHAP values).
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} layout="vertical" margin={{ left: 40, right: 60 }}>
          <XAxis
            type="number"
            tickFormatter={(v: number) => `${v >= 0 ? "+" : "−"}$${Math.abs(v / 1000)}k`}
            stroke="#64748b"
            fontSize={12}
          />
          <YAxis type="category" dataKey="label" width={150} stroke="#94a3b8" fontSize={12} />
          <Tooltip
            formatter={(v) => [signedSgd(Number(v)), "Impact"]}
            contentStyle={{
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: 8,
            }}
          />
          <ReferenceLine x={0} stroke="#475569" />
          <Bar dataKey="amount" radius={[0, 4, 4, 0]}>
            {data.map((d) => (
              <Cell key={d.label} fill={d.amount >= 0 ? "#34d399" : "#f87171"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
