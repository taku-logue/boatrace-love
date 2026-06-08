export const dynamic = "force-dynamic";

type SearchParams = Record<string, string | string[] | undefined>;

type ApiHealth = {
  status?: string;
  service?: string;
  database?: string;
};

type ModelMetadata = {
  model_name: string;
  model_version: string;
  model_view: string;
  target?: string | null;
  feature_columns: string[];
  categorical_columns: string[];
  created_at?: string | null;
  dataset_sha256?: string | null;
  schema_sha256?: string | null;
};

type PredictionEntry = {
  rank: number;
  boat_no: number;
  racer_registration_no?: string | null;
  racer_name?: string | null;
  racer_class?: string | null;
  raw_win_probability: number;
  win_probability: number;
  is_missing_period_stats: boolean;
  is_missing_pre_race: boolean;
  is_missing_weather: boolean;
  is_missing_odds: boolean;
};

type Prediction = {
  race_id: string;
  race_date?: string | null;
  venue_code?: string | null;
  race_no?: number | null;
  model_name: string;
  model_version: string;
  model_view: string;
  prediction_status: string;
  predicted_at: string;
  probability_sum: number;
  entries: PredictionEntry[];
};

type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status?: number; message: string };

const DEFAULT_RACE_ID = "20260528_01_01";

export default async function Home({
  searchParams,
}: {
  searchParams?: Promise<SearchParams>;
}) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const raceId = normalizeRaceId(resolvedSearchParams.raceId);
  const apiBaseUrl =
    process.env.API_INTERNAL_BASE_URL ?? "http://127.0.0.1:8000";

  const [apiStatus, dbStatus, model, prediction] = await Promise.all([
    fetchApi<ApiHealth>(`${apiBaseUrl}/health`),
    fetchApi<ApiHealth>(`${apiBaseUrl}/db/health`),
    fetchApi<ModelMetadata>(`${apiBaseUrl}/models/latest`),
    fetchApi<Prediction>(
      `${apiBaseUrl}/races/${encodeURIComponent(raceId)}/prediction`,
    ),
  ]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <div className="mx-auto flex w-full max-w-7xl min-w-0 flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-cyan-700">
              Local prediction console
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-normal sm:text-3xl">
              BOATRACE=LOVE
            </h1>
          </div>

          <form className="flex w-full flex-col gap-2 sm:max-w-xl sm:flex-row">
            <label className="flex-1">
              <span className="mb-1 block text-xs font-semibold text-slate-600">
                Race ID
              </span>
              <input
                name="raceId"
                defaultValue={raceId}
                className="h-11 w-full rounded border border-slate-300 bg-white px-3 text-sm font-medium outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100"
                pattern="[0-9]{8}_[0-9]{2}_[0-9]{2}"
              />
            </label>
            <button
              type="submit"
              className="mt-auto h-11 rounded bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-400"
            >
              Load Prediction
            </button>
          </form>
        </header>

        <section className="grid gap-3 md:grid-cols-3">
          <StatusPanel
            title="API"
            tone="cyan"
            result={apiStatus}
            value={apiStatus.ok ? apiStatus.data.status : "error"}
            detail={apiStatus.ok ? apiStatus.data.service : apiStatus.message}
          />
          <StatusPanel
            title="Database"
            tone="emerald"
            result={dbStatus}
            value={dbStatus.ok ? dbStatus.data.status : "error"}
            detail={dbStatus.ok ? dbStatus.data.database : dbStatus.message}
          />
          <StatusPanel
            title="Model"
            tone="violet"
            result={model}
            value={model.ok ? model.data.model_version : "error"}
            detail={model.ok ? model.data.model_name : model.message}
          />
        </section>

        <section className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="min-w-0 overflow-hidden rounded border border-slate-200 bg-white">
            <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-bold">Prediction Board</h2>
                <p className="mt-1 text-sm text-slate-600">
                  {prediction.ok
                    ? `${prediction.data.race_date ?? "-"} / Venue ${prediction.data.venue_code ?? "-"} / ${prediction.data.race_no ?? "-"}R`
                    : `Race ${raceId}`}
                </p>
              </div>
              {prediction.ok ? (
                <div className="grid grid-cols-2 gap-2 text-right text-xs sm:grid-cols-3">
                  <Metric
                    label="Entries"
                    value={prediction.data.entries.length}
                  />
                  <Metric
                    label="Prob. sum"
                    value={prediction.data.probability_sum.toFixed(6)}
                  />
                  <Metric
                    label="Status"
                    value={prediction.data.prediction_status}
                  />
                </div>
              ) : null}
            </div>

            {prediction.ok ? (
              <PredictionTable entries={prediction.data.entries} />
            ) : (
              <ErrorBlock
                title="Prediction unavailable"
                message={prediction.message}
                status={prediction.status}
              />
            )}
          </div>

          <aside className="min-w-0 flex flex-col gap-5">
            <div className="rounded border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-bold text-slate-900">
                Model Contract
              </h2>
              {model.ok ? (
                <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
                  <InfoTerm label="Name" value={model.data.model_name} />
                  <InfoTerm label="Version" value={model.data.model_version} />
                  <InfoTerm label="View" value={model.data.model_view} />
                  <InfoTerm label="Target" value={model.data.target ?? "-"} />
                  <InfoTerm
                    label="Features"
                    value={model.data.feature_columns.length}
                  />
                  <InfoTerm
                    label="Categorical"
                    value={model.data.categorical_columns.length}
                  />
                </dl>
              ) : (
                <ErrorBlock
                  title="Model unavailable"
                  message={model.message}
                  status={model.status}
                  compact
                />
              )}
            </div>

            {prediction.ok ? (
              <div className="rounded border border-slate-200 bg-white p-4">
                <h2 className="text-sm font-bold text-slate-900">Top Pick</h2>
                <div className="mt-3">
                  <p className="text-3xl font-bold text-cyan-700">
                    {prediction.data.entries[0]?.boat_no ?? "-"}号艇
                  </p>
                  <p className="mt-1 text-sm font-medium text-slate-700">
                    {prediction.data.entries[0]?.racer_name ?? "-"}
                  </p>
                  <p className="mt-3 text-2xl font-bold">
                    {formatPercent(
                      prediction.data.entries[0]?.win_probability ?? 0,
                    )}
                  </p>
                </div>
              </div>
            ) : null}
          </aside>
        </section>
      </div>
    </main>
  );
}

async function fetchApi<T>(url: string): Promise<ApiResult<T>> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    const body = (await response.json().catch(() => null)) as unknown;
    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        message: apiErrorMessage(body) ?? response.statusText,
      };
    }
    return { ok: true, data: body as T };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Request failed",
    };
  }
}

function normalizeRaceId(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] || DEFAULT_RACE_ID;
  }
  return value || DEFAULT_RACE_ID;
}

function apiErrorMessage(body: unknown): string | null {
  if (!body || typeof body !== "object") {
    return null;
  }
  const value = body as {
    message?: unknown;
    detail?: unknown;
    error_code?: unknown;
  };
  if (typeof value.message === "string") {
    return value.message;
  }
  if (typeof value.detail === "string") {
    return value.detail;
  }
  if (typeof value.error_code === "string") {
    return value.error_code;
  }
  return null;
}

function StatusPanel<T>({
  title,
  tone,
  result,
  value,
  detail,
}: {
  title: string;
  tone: "cyan" | "emerald" | "violet";
  result: ApiResult<T>;
  value?: string;
  detail?: string;
}) {
  const dotClass = result.ok
    ? {
        cyan: "bg-cyan-500",
        emerald: "bg-emerald-500",
        violet: "bg-violet-500",
      }[tone]
    : "bg-rose-500";

  return (
    <div className="rounded border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-bold text-slate-800">{title}</h2>
        <span className={`h-2.5 w-2.5 rounded-full ${dotClass}`} />
      </div>
      <p className="mt-3 break-words text-lg font-bold">{value ?? "-"}</p>
      <p className="mt-1 min-h-5 break-words text-xs text-slate-500">
        {detail ?? "-"}
      </p>
    </div>
  );
}

function PredictionTable({ entries }: { entries: PredictionEntry[] }) {
  return (
    <div className="w-full max-w-full overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-sm">
        <thead className="bg-slate-100 text-left text-xs uppercase text-slate-600">
          <tr>
            <th className="px-4 py-3">Rank</th>
            <th className="px-4 py-3">Boat</th>
            <th className="px-4 py-3">Racer</th>
            <th className="px-4 py-3">Class</th>
            <th className="px-4 py-3">Win Prob.</th>
            <th className="px-4 py-3">Raw Prob.</th>
            <th className="px-4 py-3">Missing</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr
              key={entry.boat_no}
              className="border-t border-slate-200 hover:bg-slate-50"
            >
              <td className="px-4 py-3 font-bold text-slate-900">
                {entry.rank}
              </td>
              <td className="px-4 py-3">
                <span className="inline-flex h-8 w-8 items-center justify-center rounded border border-slate-300 bg-white font-bold">
                  {entry.boat_no}
                </span>
              </td>
              <td className="px-4 py-3">
                <div className="font-semibold text-slate-900">
                  {entry.racer_name ?? "-"}
                </div>
                <div className="text-xs text-slate-500">
                  {entry.racer_registration_no ?? "-"}
                </div>
              </td>
              <td className="px-4 py-3 font-medium">
                {entry.racer_class ?? "-"}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="h-2 w-24 rounded bg-slate-200">
                    <div
                      className="h-2 rounded bg-cyan-600"
                      style={{
                        width: `${Math.round(entry.win_probability * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="w-16 text-right font-bold">
                    {formatPercent(entry.win_probability)}
                  </span>
                </div>
              </td>
              <td className="px-4 py-3 text-slate-600">
                {formatPercent(entry.raw_win_probability)}
              </td>
              <td className="px-4 py-3">
                <MissingFlags entry={entry} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MissingFlags({ entry }: { entry: PredictionEntry }) {
  const flags = [
    entry.is_missing_period_stats ? "period" : null,
    entry.is_missing_pre_race ? "pre-race" : null,
    entry.is_missing_weather ? "weather" : null,
    entry.is_missing_odds ? "odds" : null,
  ].filter(Boolean);

  if (flags.length === 0) {
    return <span className="text-xs font-semibold text-emerald-700">none</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {flags.map((flag) => (
        <span
          key={flag}
          className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-800"
        >
          {flag}
        </span>
      ))}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="text-[11px] font-semibold uppercase text-slate-500">
        {label}
      </div>
      <div className="mt-1 font-bold text-slate-900">{value}</div>
    </div>
  );
}

function InfoTerm({ label, value }: { label: string; value: string | number }) {
  return (
    <>
      <dt className="text-xs font-semibold text-slate-500">{label}</dt>
      <dd className="break-words text-sm font-bold text-slate-900">{value}</dd>
    </>
  );
}

function ErrorBlock({
  title,
  message,
  status,
  compact = false,
}: {
  title: string;
  message: string;
  status?: number;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "py-3" : "px-4 py-10"}>
      <div className="rounded border border-rose-200 bg-rose-50 p-4">
        <h3 className="font-bold text-rose-900">{title}</h3>
        <p className="mt-1 text-sm text-rose-800">
          {status ? `${status}: ` : ""}
          {message}
        </p>
      </div>
    </div>
  );
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
