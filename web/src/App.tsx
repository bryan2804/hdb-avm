import { useEffect, useState } from "react";
import {
  ApiError,
  createValuation,
  getMetadata,
  getTrends,
  type Metadata,
  type TrendsResponse,
  type ValuationRequest,
  type ValuationResponse,
} from "./api";
import ContributionsChart from "./components/ContributionsChart";
import TrendsChart from "./components/TrendsChart";
import ValuationForm from "./components/ValuationForm";
import ValuationResult from "./components/ValuationResult";

function Card({ children }: { children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
      {children}
    </section>
  );
}

export default function App() {
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [slowStart, setSlowStart] = useState(false);
  const [valuation, setValuation] = useState<ValuationResponse | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const slowTimer = setTimeout(() => setSlowStart(true), 4000);
    getMetadata()
      .then(setMetadata)
      .catch(() => setMetadataError("API unavailable — is the backend running?"))
      .finally(() => clearTimeout(slowTimer));
    return () => clearTimeout(slowTimer);
  }, []);

  const handleSubmit = async (req: ValuationRequest) => {
    setLoading(true);
    setError(null);
    try {
      const [v, t] = await Promise.all([
        createValuation(req),
        getTrends(req.town, req.flat_type).catch(() => null),
      ]);
      setValuation(v);
      setTrends(t);
    } catch (e) {
      setValuation(null);
      setTrends(null);
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">HDB Automated Valuation Model</h1>
        <p className="mt-1 text-sm text-slate-400">
          232,000+ resale transactions · XGBoost with exact TreeSHAP explanations · modelled on
          collateral validation tools used by bank home loan teams
          {metadata?.trained_at && (
            <span> · model trained {metadata.trained_at}</span>
          )}
        </p>
      </header>

      {metadataError && (
        <div className="mb-6 rounded-lg border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">
          {metadataError}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-[380px_1fr]">
        <Card>
          {metadata ? (
            <ValuationForm metadata={metadata} loading={loading} onSubmit={handleSubmit} />
          ) : (
            !metadataError && (
              <div className="text-sm text-slate-500">
                Loading model metadata…
                {slowStart && (
                  <span className="mt-1 block text-xs text-slate-600">
                    First load can take up to a minute — the free-tier API server wakes up from
                    sleep on the first request.
                  </span>
                )}
              </div>
            )
          )}
        </Card>

        <div className="space-y-6">
          {error && (
            <div className="rounded-lg border border-amber-900 bg-amber-950/40 p-4 text-sm text-amber-300">
              {error}
            </div>
          )}
          {valuation ? (
            <>
              <Card>
                <ValuationResult valuation={valuation} />
              </Card>
              <Card>
                <ContributionsChart valuation={valuation} />
              </Card>
              {trends && (
                <Card>
                  <TrendsChart trends={trends} />
                </Card>
              )}
            </>
          ) : (
            !error && (
              <Card>
                <p className="text-sm text-slate-500">
                  Set the flat's attributes and get a valuation with a confidence band and a
                  breakdown of what drives the price. Add a block address for block-level
                  precision.
                </p>
              </Card>
            )
          )}
        </div>
      </div>

      <footer className="mt-10 text-center text-xs text-slate-600">
        Data: data.gov.sg resale transactions · Geocoding: OneMap ·{" "}
        <a
          href="https://github.com/bryan2804/hdb-avm"
          className="underline hover:text-slate-400"
        >
          github.com/bryan2804/hdb-avm
        </a>
      </footer>
    </div>
  );
}
