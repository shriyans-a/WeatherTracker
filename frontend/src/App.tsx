import { useState } from 'react'
import axios from 'axios'

type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Extreme'

interface ApiAlert {
  id: string
  event: string
  severity: 'Minor' | 'Moderate' | 'Severe' | 'Extreme'
  headline?: string
  description?: string
  instruction?: string
}

interface ApiCurrentConditions {
  temperature_c?: number
  wind_speed_kph?: number
  wind_direction?: string
  short_description?: string
  detailed_description?: string
}

interface ApiShortTermPeriod {
  name: string
  start_time: string
  end_time: string
  temperature_c?: number
  wind_speed_kph?: number
  wind_direction?: string
  short_description?: string
}

interface ApiShortTermForecast {
  periods: ApiShortTermPeriod[]
}

interface ApiAI {
  explanation: string
  recommendations: string[]
}

interface ApiResponse {
  location: string
  coordinates: { latitude: number; longitude: number }
  current_conditions: ApiCurrentConditions
  short_term_forecast: ApiShortTermForecast
  alerts: ApiAlert[]
  risk_score: number
  risk_level: RiskLevel
  ai: ApiAI
}

const riskLevelColors: Record<
  RiskLevel,
  { badge: string; bar: string; bg: string }
> = {
  Low: {
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    bar: 'bg-emerald-500',
    bg: 'from-emerald-50 to-white',
  },
  Moderate: {
    badge: 'bg-amber-100 text-amber-800 border-amber-200',
    bar: 'bg-amber-500',
    bg: 'from-amber-50 to-white',
  },
  High: {
    badge: 'bg-orange-100 text-orange-800 border-orange-200',
    bar: 'bg-orange-500',
    bg: 'from-orange-50 to-white',
  },
  Extreme: {
    badge: 'bg-red-100 text-red-800 border-red-200',
    bar: 'bg-red-600',
    bg: 'from-red-50 to-white',
  },
}

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<ApiResponse | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setData(null)

    try {
      const resp = await axios.post<ApiResponse>('http://localhost:8000/api/assess-risk', {
        location: query.trim(),
      })
      setData(resp.data)
    } catch (err: any) {
      const message =
        err.response?.data?.detail ||
        err.message ||
        'Something went wrong while assessing risk.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const riskStyles =
    data?.risk_level && riskLevelColors[data.risk_level]
      ? riskLevelColors[data.risk_level]
      : riskLevelColors.Low

  return (
    <div className="min-h-screen bg-slate-950 py-10 px-4">
      <div className="mx-auto max-w-5xl space-y-8">
        <header className="flex flex-col gap-3 text-center">
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-50">
            Neighborhood Weather Risk
          </h1>
          <p className="text-sm md:text-base text-slate-400 max-w-2xl mx-auto">
            Real-time National Weather Service data, transparent risk scoring, and
            Gradient AI explanations—so residents understand what&apos;s happening right
            now and what to do next.
          </p>
        </header>

        <main className="grid gap-6 md:grid-cols-[1.3fr,1fr] items-start">
          <section
            className={`rounded-2xl border border-slate-800 bg-gradient-to-br ${riskStyles.bg} p-5 md:p-6 shadow-xl shadow-black/40`}
          >
            <form
              onSubmit={handleSubmit}
              className="flex flex-col gap-3 sm:flex-row sm:items-center"
            >
              <div className="relative flex-1">
                <input
                  type="text"
                  placeholder="Enter city or ZIP (e.g., Seattle or 98101)"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-2.5 pr-10 text-sm text-slate-50 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/40"
                />
                <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-500 text-xs">
                  ⏎
                </span>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="inline-flex items-center justify-center rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-medium text-slate-950 shadow-lg shadow-sky-500/40 hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {loading ? 'Assessing…' : 'Assess risk'}
              </button>
            </form>

            {error && (
              <div className="mt-4 rounded-xl border border-red-500/40 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}

            {data && (
              <div className="mt-5 space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                      Location
                    </p>
                    <p className="text-sm font-medium text-slate-50">
                      {data.location}
                      <span className="ml-2 text-xs text-slate-400">
                        ({data.coordinates.latitude.toFixed(3)},{' '}
                        {data.coordinates.longitude.toFixed(3)})
                      </span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium ${riskStyles.badge}`}
                    >
                      <span
                        className={`h-2 w-2 rounded-full ${
                          data.risk_level === 'Extreme'
                            ? 'bg-red-500 animate-pulse'
                            : data.risk_level === 'High'
                              ? 'bg-orange-400 animate-pulse'
                              : data.risk_level === 'Moderate'
                                ? 'bg-amber-400'
                                : 'bg-emerald-400'
                        }`}
                      />
                      {data.risk_level} risk
                    </span>
                    <span className="text-xs text-slate-400">
                      Score:{' '}
                      <span className="font-semibold text-slate-100">
                        {data.risk_score}
                      </span>
                      /100
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-[11px] uppercase tracking-[0.2em] text-slate-500">
                    <span>Risk score</span>
                    <span>0 — 100</span>
                  </div>
                  <div className="h-2.5 w-full rounded-full bg-slate-900/80">
                    <div
                      className={`h-full rounded-full ${riskStyles.bar}`}
                      style={{ width: `${Math.min(100, Math.max(0, data.risk_score))}%` }}
                    />
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
                      Current conditions
                    </p>
                    <div className="mt-2 space-y-1.5 text-sm text-slate-100">
                      <p className="text-base font-medium">
                        {data.current_conditions.short_description || 'N/A'}
                      </p>
                      {data.current_conditions.temperature_c != null && (
                        <p className="text-sm text-slate-300">
                          Temperature:{' '}
                          <span className="font-medium">
                            {data.current_conditions.temperature_c.toFixed(1)} °C
                          </span>
                        </p>
                      )}
                      {data.current_conditions.wind_speed_kph != null && (
                        <p className="text-sm text-slate-300">
                          Wind:{' '}
                          <span className="font-medium">
                            {data.current_conditions.wind_speed_kph.toFixed(0)} km/h
                          </span>{' '}
                          {data.current_conditions.wind_direction &&
                            `from ${data.current_conditions.wind_direction}`}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
                      Next hours
                    </p>
                    <div className="mt-2 space-y-2 text-xs text-slate-200">
                      {data.short_term_forecast.periods.slice(0, 3).map((p) => (
                        <div
                          key={p.start_time}
                          className="flex items-center justify-between gap-3 rounded-lg bg-slate-900/80 px-3 py-2"
                        >
                          <div className="space-y-0.5">
                            <p className="text-[11px] font-semibold text-slate-100">
                              {p.name}
                            </p>
                            <p className="text-[11px] text-slate-400">
                              {p.short_description || '—'}
                            </p>
                          </div>
                          <div className="text-right text-[11px] text-slate-300">
                            {p.temperature_c != null && (
                              <p>{p.temperature_c.toFixed(0)} °C</p>
                            )}
                            {p.wind_speed_kph != null && (
                              <p>{p.wind_speed_kph.toFixed(0)} km/h</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
                      Alerts
                    </p>
                    {data.alerts.length === 0 ? (
                      <p className="mt-3 text-sm text-slate-300">
                        No active NWS alerts for this point.
                      </p>
                    ) : (
                      <div className="mt-3 space-y-3">
                        {data.alerts.map((a) => (
                          <div
                            key={a.id}
                            className="rounded-lg border border-slate-700 bg-slate-900/80 p-3 text-xs text-left"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <p className="font-semibold text-slate-100">{a.event}</p>
                              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] uppercase tracking-[0.16em] text-slate-300">
                                {a.severity}
                              </span>
                            </div>
                            {a.headline && (
                              <p className="mt-1 text-[11px] text-slate-300">
                                {a.headline}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
                      AI guidance
                    </p>
                    <div className="mt-2 space-y-3 text-sm text-slate-100">
                      <p className="text-sm text-slate-200">{data.ai.explanation}</p>
                      {data.ai.recommendations.length > 0 && (
                        <ul className="mt-1 space-y-1.5 text-xs text-slate-200">
                          {data.ai.recommendations.slice(0, 3).map((r, idx) => (
                            <li key={idx} className="flex gap-2">
                              <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-400" />
                              <span>{r}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!data && !error && !loading && (
              <p className="mt-5 text-xs text-slate-400">
                Try something like <span className="font-mono text-slate-200">94103</span>{' '}
                or <span className="font-mono text-slate-200">Austin, TX</span> to see
                real-time risk.
              </p>
            )}
          </section>

          <aside className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/80 p-4 md:p-5 shadow-xl shadow-black/40">
            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
                How this works
              </p>
              <ul className="mt-3 space-y-2 text-xs text-slate-300">
                <li>
                  <span className="font-semibold text-slate-100">
                    1. Real-time data:
                  </span>{' '}
                  We geocode your location and call the National Weather Service for
                  forecast + active alerts.
                </li>
                <li>
                  <span className="font-semibold text-slate-100">
                    2. Transparent scoring:
                  </span>{' '}
                  A rule-based engine scores short-term hazards (wind, storms, heat,
                  precipitation) and alert severity from 0–100.
                </li>
                <li>
                  <span className="font-semibold text-slate-100">
                    3. Gradient AI layer:
                  </span>{' '}
                  DigitalOcean Gradient AI turns the raw hazard data into a plain-English
                  explanation and concrete next steps.
                </li>
              </ul>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-[11px] text-slate-400">
              Designed as a simple, rule-driven pipeline so you can audit inputs,
              understand how the score is produced, and swap models without changing the
              data layer.
            </div>
          </aside>
        </main>
      </div>
    </div>
  )
}

export default App
