import { useState, type FormEvent } from "react";
import type { Metadata, ValuationRequest } from "../api";

interface Props {
  metadata: Metadata;
  loading: boolean;
  onSubmit: (req: ValuationRequest) => void;
}

function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-slate-300">{label}</span>
        <span className="font-medium text-slate-100">
          {value}
          {unit ? ` ${unit}` : ""}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-emerald-400"
      />
    </label>
  );
}

export default function ValuationForm({ metadata, loading, onSubmit }: Props) {
  const [town, setTown] = useState("ANG MO KIO");
  const [flatType, setFlatType] = useState("4 ROOM");
  const [floorArea, setFloorArea] = useState(90);
  const [storey, setStorey] = useState(10);
  const [lease, setLease] = useState(75);
  const [address, setAddress] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit({
      town,
      flat_type: flatType,
      floor_area_sqm: floorArea,
      storey,
      remaining_lease_years: lease,
      ...(address.trim() ? { address: address.trim() } : {}),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <label className="block text-sm">
          <span className="mb-1 block text-slate-300">Town</span>
          <select
            value={town}
            onChange={(e) => setTown(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
          >
            {metadata.towns.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          <span className="mt-1 block text-xs text-slate-600">
            Only towns with resale history are listed — e.g. Tengah has none yet, so it isn't
            priceable.
          </span>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-300">Flat type</span>
          <select
            value={flatType}
            onChange={(e) => setFlatType(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
          >
            {metadata.flat_types.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
      </div>

      <Slider label="Floor area" value={floorArea} min={30} max={200} unit="sqm" onChange={setFloorArea} />
      <Slider label="Storey" value={storey} min={1} max={50} onChange={setStorey} />
      <Slider label="Remaining lease" value={lease} min={40} max={99} unit="years" onChange={setLease} />

      <label className="block text-sm">
        <span className="mb-1 block text-slate-300">
          Block address <span className="text-slate-500">(optional — enables block-level precision)</span>
        </span>
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="e.g. 406 ANG MO KIO AVE 10"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 placeholder:text-slate-600"
        />
      </label>

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-emerald-500 py-2.5 font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-50"
      >
        {loading ? "Valuing…" : "Get valuation"}
      </button>
    </form>
  );
}
