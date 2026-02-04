"use client";

import Link from "next/link";
import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Settings } from "lucide-react";
import { useRouter } from "next/navigation";

const AVAILABLE_METRICS = [
  { value: "readiness_score", label: "Readiness Score" },
  { value: "sleep_score", label: "Sleep Score" },
  { value: "activity_score", label: "Activity Score" },
  { value: "steps", label: "Steps" },
  { value: "hrv_average", label: "HRV Average" },
  { value: "hr_lowest", label: "Resting Heart Rate" },
  { value: "sleep_total_seconds", label: "Sleep Duration" },
  { value: "sleep_efficiency", label: "Sleep Efficiency" },
  { value: "sleep_deep_seconds", label: "Deep Sleep" },
  { value: "sleep_rem_seconds", label: "REM Sleep" },
  { value: "cal_total", label: "Total Calories" },
  { value: "cal_active", label: "Active Calories" },
];

interface SpearmanCorrelation {
  metric: string;
  rho: number;
  p_value: number;
  n: number;
}

interface LaggedCorrelation {
  lag: number;
  rho: number;
  p_value: number;
  n: number;
}

interface ControlledResult {
  metric_x: string;
  metric_y: string;
  rho: number;
  p_value: number;
  n: number;
  controlled_for: string[];
}

export default function CorrelationsPage() {
  const router = useRouter();
  // Spearman state
  const [spearmanTarget, setSpearmanTarget] = useState("readiness_score");
  const [spearmanCandidates, setSpearmanCandidates] = useState<string[]>([
    "sleep_score",
    "hrv_average",
    "steps",
    "sleep_total_seconds",
  ]);
  const [spearmanResults, setSpearmanResults] = useState<SpearmanCorrelation[] | null>(null);
  const [spearmanLoading, setSpearmanLoading] = useState(false);

  // Lagged state
  const [laggedX, setLaggedX] = useState("steps");
  const [laggedY, setLaggedY] = useState("sleep_score");
  const [maxLag, setMaxLag] = useState(7);
  const [laggedResults, setLaggedResults] = useState<{
    lags: LaggedCorrelation[];
    best_lag: number;
  } | null>(null);
  const [laggedLoading, setLaggedLoading] = useState(false);

  // Controlled state
  const [controlledX, setControlledX] = useState("hrv_average");
  const [controlledY, setControlledY] = useState("readiness_score");
  const [controlVars, setControlVars] = useState<string[]>(["sleep_total_seconds"]);
  const [controlledResult, setControlledResult] = useState<ControlledResult | null>(null);
  const [controlledLoading, setControlledLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_ANALYTICS_URL || "http://localhost:8001";

  const runSpearman = async () => {
    setSpearmanLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append("target", spearmanTarget);
      spearmanCandidates.forEach((c) => params.append("candidates", c));

      const response = await fetch(`${apiUrl}/analyze/correlations/spearman?${params}`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to compute correlations");
      const data = await response.json();
      setSpearmanResults(data.correlations);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSpearmanLoading(false);
    }
  };

  const runLagged = async () => {
    setLaggedLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        metric_x: laggedX,
        metric_y: laggedY,
        max_lag: maxLag.toString(),
      });

      const response = await fetch(`${apiUrl}/analyze/correlations/lagged?${params}`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to compute lagged correlations");
      const data = await response.json();
      setLaggedResults({ lags: data.lags, best_lag: data.best_lag });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLaggedLoading(false);
    }
  };

  const runControlled = async () => {
    setControlledLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append("metric_x", controlledX);
      params.append("metric_y", controlledY);
      controlVars.forEach((v) => params.append("control_vars", v));

      const response = await fetch(`${apiUrl}/analyze/correlations/controlled?${params}`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to compute controlled correlation");
      const data = await response.json();
      setControlledResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setControlledLoading(false);
    }
  };

  const toggleCandidate = (metric: string) => {
    setSpearmanCandidates((prev) =>
      prev.includes(metric) ? prev.filter((m) => m !== metric) : [...prev, metric]
    );
  };

  const toggleControlVar = (metric: string) => {
    setControlVars((prev) =>
      prev.includes(metric) ? prev.filter((m) => m !== metric) : [...prev, metric]
    );
  };

  const getMetricLabel = (value: string) =>
    AVAILABLE_METRICS.find((m) => m.value === value)?.label || value;

  const getCorrelationColor = (rho: number) => {
    if (rho > 0.5) return "#16a34a";
    if (rho > 0.3) return "#65a30d";
    if (rho > 0) return "#84cc16";
    if (rho > -0.3) return "#f97316";
    if (rho > -0.5) return "#ea580c";
    return "#dc2626";
  };

  const formatPValue = (p: number) => {
    if (p < 0.001) return "< 0.001";
    return p.toFixed(3);
  };

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Correlations</h1>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Select value="correlations" onValueChange={(value) => router.push(`/${value}`)}>
            <SelectTrigger className="w-[145px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="dashboard">Dashboard</SelectItem>
              <SelectItem value="correlations">Correlations</SelectItem>
              <SelectItem value="patterns">Patterns</SelectItem>
              <SelectItem value="insights">Insights</SelectItem>
            </SelectContent>
          </Select>
          <Link href="/settings">
            <Button variant="outline" size="icon">
              <Settings className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <Tabs defaultValue="spearman" className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-4">
          <TabsTrigger value="spearman">Spearman</TabsTrigger>
          <TabsTrigger value="lagged">Lagged</TabsTrigger>
          <TabsTrigger value="controlled">Controlled</TabsTrigger>
        </TabsList>

        {/* Spearman Correlations */}
        <TabsContent value="spearman">
          <Card>
            <CardHeader>
              <CardTitle>Spearman Rank Correlations</CardTitle>
              <CardDescription>
                Find which metrics are most correlated with your target metric
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Target Metric</label>
                <select
                  value={spearmanTarget}
                  onChange={(e) => setSpearmanTarget(e.target.value)}
                  className="w-full border rounded px-3 py-2 bg-background"
                >
                  {AVAILABLE_METRICS.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Candidate Metrics</label>
                <div className="flex flex-wrap gap-2">
                  {AVAILABLE_METRICS.filter((m) => m.value !== spearmanTarget).map((m) => (
                    <Badge
                      key={m.value}
                      variant={spearmanCandidates.includes(m.value) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => toggleCandidate(m.value)}
                    >
                      {m.label}
                    </Badge>
                  ))}
                </div>
              </div>

              <Button onClick={runSpearman} disabled={spearmanLoading || spearmanCandidates.length === 0}>
                {spearmanLoading ? "Computing..." : "Compute Correlations"}
              </Button>

              {spearmanResults && (
                <div className="mt-6">
                  <h4 className="text-sm font-medium mb-4">
                    Correlations with {getMetricLabel(spearmanTarget)}
                  </h4>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={spearmanResults
                          .map((r) => ({
                            metric: getMetricLabel(r.metric),
                            rho: r.rho,
                            p_value: r.p_value,
                            n: r.n,
                          }))
                          .sort((a, b) => Math.abs(b.rho) - Math.abs(a.rho))}
                        layout="vertical"
                        margin={{ left: 120 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis type="number" domain={[-1, 1]} />
                        <YAxis type="category" dataKey="metric" tick={{ fontSize: 12 }} width={110} />
                        <Tooltip
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const data = payload[0].payload;
                              return (
                                <div className="bg-card border rounded p-2 text-sm">
                                  <p className="font-medium">{data.metric}</p>
                                  <p>ρ = {data.rho.toFixed(3)}</p>
                                  <p>p = {formatPValue(data.p_value)}</p>
                                  <p>n = {data.n}</p>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <ReferenceLine x={0} stroke="#888" />
                        <Bar dataKey="rho" name="Correlation">
                          {spearmanResults.map((entry, index) => (
                            <Cell key={index} fill={getCorrelationColor(entry.rho)} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Green = positive correlation, Orange/Red = negative correlation. Stronger colors = stronger correlation.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Lagged Correlations */}
        <TabsContent value="lagged">
          <Card>
            <CardHeader>
              <CardTitle>Lagged Correlations</CardTitle>
              <CardDescription>
                Find if metric X predicts metric Y days later (e.g., does exercise today predict better sleep tomorrow?)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Predictor (X)</label>
                  <select
                    value={laggedX}
                    onChange={(e) => setLaggedX(e.target.value)}
                    className="w-full border rounded px-3 py-2 bg-background"
                  >
                    {AVAILABLE_METRICS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Target (Y)</label>
                  <select
                    value={laggedY}
                    onChange={(e) => setLaggedY(e.target.value)}
                    className="w-full border rounded px-3 py-2 bg-background"
                  >
                    {AVAILABLE_METRICS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Max Lag (days)</label>
                <input
                  type="number"
                  value={maxLag}
                  onChange={(e) => setMaxLag(parseInt(e.target.value) || 7)}
                  min={1}
                  max={30}
                  className="w-24 border rounded px-3 py-2 bg-background"
                />
              </div>

              <Button onClick={runLagged} disabled={laggedLoading}>
                {laggedLoading ? "Computing..." : "Compute Lagged Correlations"}
              </Button>

              {laggedResults && (
                <div className="mt-6">
                  <div className="flex items-center gap-2 mb-4">
                    <h4 className="text-sm font-medium">
                      {getMetricLabel(laggedX)} → {getMetricLabel(laggedY)}
                    </h4>
                    <Badge variant="secondary">Best lag: {laggedResults.best_lag} days</Badge>
                  </div>
                  <div className="h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={laggedResults.lags}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis
                          dataKey="lag"
                          label={{ value: "Lag (days)", position: "bottom", offset: -5 }}
                        />
                        <YAxis domain={[-1, 1]} />
                        <Tooltip
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const data = payload[0].payload;
                              return (
                                <div className="bg-card border rounded p-2 text-sm">
                                  <p className="font-medium">Lag: {data.lag} days</p>
                                  <p>ρ = {data.rho.toFixed(3)}</p>
                                  <p>p = {formatPValue(data.p_value)}</p>
                                  <p>n = {data.n}</p>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <ReferenceLine y={0} stroke="#888" />
                        <Bar dataKey="rho" name="Correlation">
                          {laggedResults.lags.map((entry, index) => (
                            <Cell
                              key={index}
                              fill={
                                entry.lag === laggedResults.best_lag
                                  ? "#2563eb"
                                  : getCorrelationColor(entry.rho)
                              }
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Lag 0 = same day. Lag 1 = X predicts Y the next day. Blue bar = strongest correlation.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Controlled Correlations */}
        <TabsContent value="controlled">
          <Card>
            <CardHeader>
              <CardTitle>Controlled (Partial) Correlations</CardTitle>
              <CardDescription>
                Find the true correlation between X and Y while controlling for confounding variables
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Metric X</label>
                  <select
                    value={controlledX}
                    onChange={(e) => setControlledX(e.target.value)}
                    className="w-full border rounded px-3 py-2 bg-background"
                  >
                    {AVAILABLE_METRICS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Metric Y</label>
                  <select
                    value={controlledY}
                    onChange={(e) => setControlledY(e.target.value)}
                    className="w-full border rounded px-3 py-2 bg-background"
                  >
                    {AVAILABLE_METRICS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Control Variables</label>
                <div className="flex flex-wrap gap-2">
                  {AVAILABLE_METRICS.filter(
                    (m) => m.value !== controlledX && m.value !== controlledY
                  ).map((m) => (
                    <Badge
                      key={m.value}
                      variant={controlVars.includes(m.value) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => toggleControlVar(m.value)}
                    >
                      {m.label}
                    </Badge>
                  ))}
                </div>
              </div>

              <Button onClick={runControlled} disabled={controlledLoading || controlVars.length === 0}>
                {controlledLoading ? "Computing..." : "Compute Partial Correlation"}
              </Button>

              {controlledResult && (
                <div className="mt-6 p-4 border rounded-lg">
                  <h4 className="text-lg font-medium mb-4">Result</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Correlation (ρ)</p>
                      <p
                        className="text-2xl font-bold"
                        style={{ color: getCorrelationColor(controlledResult.rho) }}
                      >
                        {controlledResult.rho.toFixed(3)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">P-value</p>
                      <p className="text-2xl font-bold">
                        {formatPValue(controlledResult.p_value)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-4">
                    <p className="text-sm text-muted-foreground">Relationship</p>
                    <p className="font-medium">
                      {getMetricLabel(controlledResult.metric_x)} ↔{" "}
                      {getMetricLabel(controlledResult.metric_y)}
                    </p>
                    <p className="text-sm text-muted-foreground mt-2">Controlling for:</p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {controlledResult.controlled_for.map((v) => (
                        <Badge key={v} variant="secondary">
                          {getMetricLabel(v)}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-4">
                    Sample size: {controlledResult.n} days.{" "}
                    {controlledResult.p_value < 0.05
                      ? "Statistically significant (p < 0.05)"
                      : "Not statistically significant (p ≥ 0.05)"}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
