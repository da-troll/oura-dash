"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
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

interface DashboardSummary {
  readiness_avg: number | null;
  sleep_score_avg: number | null;
  activity_avg: number | null;
  steps_avg: number | null;
  hrv_avg: number | null;
  rhr_avg: number | null;
  sleep_hours_avg: number | null;
  calories_avg: number | null;
  days_with_data: number;
}

interface TrendPoint {
  date: string;
  value: number | null;
}

interface TrendSeries {
  name: string;
  data: TrendPoint[];
}

interface DashboardData {
  connected: boolean;
  summary: DashboardSummary;
  trends: TrendSeries[];
}

const CHART_COLORS = {
  readiness: "#2563eb",
  sleep: "#7c3aed",
  activity: "#16a34a",
  steps: "#ea580c",
  hrv: "#0891b2",
  rhr: "#dc2626",
  sleep_hours: "#8b5cf6",
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDashboard() {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_ANALYTICS_URL || "http://localhost:8001"}/dashboard`
        );
        if (!response.ok) {
          throw new Error("Failed to fetch dashboard data");
        }
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }
    fetchDashboard();
  }, []);

  const formatValue = (value: number | null | undefined, suffix = "") => {
    if (value === null || value === undefined) return "--";
    return `${Math.round(value)}${suffix}`;
  };

  const getTrendData = (name: string) => {
    const series = data?.trends.find((t) => t.name === name);
    return (
      series?.data.map((point) => ({
        date: point.date.slice(5), // MM-DD format
        value: point.value,
      })) || []
    );
  };

  const hasData = data?.connected && data.summary.days_with_data > 0;

  const renderChart = (
    name: string,
    title: string,
    color: string,
    domain?: [number, number],
    isBar = false
  ) => {
    const chartData = getTrendData(name);
    if (!hasData || chartData.length === 0) {
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          <p>No data available</p>
        </div>
      );
    }

    if (isBar) {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10 }}
              interval="preserveStartEnd"
              className="text-muted-foreground"
            />
            <YAxis tick={{ fontSize: 10 }} domain={domain} className="text-muted-foreground" />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "6px",
              }}
            />
            <Bar dataKey="value" fill={color} name={title} radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      );
    }

    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
            className="text-muted-foreground"
          />
          <YAxis tick={{ fontSize: 10 }} domain={domain} className="text-muted-foreground" />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "6px",
            }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={{ fill: color, r: 2 }}
            name={title}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link href="/correlations">
            <Button variant="outline">Correlations</Button>
          </Link>
          <Link href="/patterns">
            <Button variant="outline">Patterns</Button>
          </Link>
          <Link href="/settings">
            <Button variant="outline">Settings</Button>
          </Link>
        </div>
      </div>

      {loading && (
        <div className="text-center text-muted-foreground py-12">Loading...</div>
      )}

      {error && (
        <div className="text-center text-red-500 py-12">Error: {error}</div>
      )}

      {!loading && !error && !hasData && (
        <Card>
          <CardContent className="h-[200px] flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <p>Connect your Oura Ring and sync data to see your dashboard</p>
              <Link href="/settings" className="mt-2 inline-block">
                <Button variant="link">Go to Settings</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {!loading && !error && hasData && (
        <>
          {/* Summary Cards - compact horizontal layout */}
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4 mb-6">
            <Card className="py-3">
              <CardContent className="flex items-center justify-between p-0 px-4">
                <span className="text-sm font-medium">Readiness</span>
                <div className="text-right">
                  <div className="text-xl font-bold">{formatValue(data?.summary.readiness_avg)}</div>
                  <p className="text-xs text-muted-foreground">7-day avg</p>
                </div>
              </CardContent>
            </Card>

            <Card className="py-3">
              <CardContent className="flex items-center justify-between p-0 px-4">
                <span className="text-sm font-medium">Sleep Score</span>
                <div className="text-right">
                  <div className="text-xl font-bold">{formatValue(data?.summary.sleep_score_avg)}</div>
                  <p className="text-xs text-muted-foreground">7-day avg</p>
                </div>
              </CardContent>
            </Card>

            <Card className="py-3">
              <CardContent className="flex items-center justify-between p-0 px-4">
                <span className="text-sm font-medium">Activity</span>
                <div className="text-right">
                  <div className="text-xl font-bold">{formatValue(data?.summary.activity_avg)}</div>
                  <p className="text-xs text-muted-foreground">7-day avg</p>
                </div>
              </CardContent>
            </Card>

            <Card className="py-3">
              <CardContent className="flex items-center justify-between p-0 px-4">
                <span className="text-sm font-medium">Steps</span>
                <div className="text-right">
                  <div className="text-xl font-bold">{formatValue(data?.summary.steps_avg)}</div>
                  <p className="text-xs text-muted-foreground">7-day avg</p>
                </div>
              </CardContent>
            </Card>

            <Card className="py-3">
              <CardContent className="flex items-center justify-between p-0 px-4">
                <span className="text-sm font-medium">HRV</span>
                <div className="text-right">
                  <div className="text-xl font-bold">{formatValue(data?.summary.hrv_avg, " ms")}</div>
                  <p className="text-xs text-muted-foreground">7-day avg</p>
                </div>
              </CardContent>
            </Card>

            <Card className="py-3">
              <CardContent className="flex items-center justify-between p-0 px-4">
                <span className="text-sm font-medium">Resting HR</span>
                <div className="text-right">
                  <div className="text-xl font-bold">{formatValue(data?.summary.rhr_avg, " bpm")}</div>
                  <p className="text-xs text-muted-foreground">7-day avg</p>
                </div>
              </CardContent>
            </Card>

            <Card className="py-3">
              <CardContent className="flex items-center justify-between p-0 px-4">
                <span className="text-sm font-medium">Sleep</span>
                <div className="text-right">
                  <div className="text-xl font-bold">
                    {data?.summary.sleep_hours_avg ? `${data.summary.sleep_hours_avg.toFixed(1)}h` : "--"}
                  </div>
                  <p className="text-xs text-muted-foreground">7-day avg</p>
                </div>
              </CardContent>
            </Card>

            <Card className="py-3">
              <CardContent className="flex items-center justify-between p-0 px-4">
                <span className="text-sm font-medium">Calories</span>
                <div className="text-right">
                  <div className="text-xl font-bold">{formatValue(data?.summary.calories_avg)}</div>
                  <p className="text-xs text-muted-foreground">7-day avg</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Trend Charts with Tabs */}
          <Card>
            <CardHeader>
              <CardTitle>Trends</CardTitle>
              <CardDescription>Your metrics over the past 60 days</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="scores" className="w-full">
                <TabsList className="grid w-full grid-cols-4 mb-4">
                  <TabsTrigger value="scores">Scores</TabsTrigger>
                  <TabsTrigger value="activity">Activity</TabsTrigger>
                  <TabsTrigger value="heart">Heart</TabsTrigger>
                  <TabsTrigger value="sleep">Sleep</TabsTrigger>
                </TabsList>

                <TabsContent value="scores" className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <h4 className="text-sm font-medium mb-2">Readiness Score</h4>
                      <div className="h-[200px]">
                        {renderChart("readiness", "Readiness", CHART_COLORS.readiness, [40, 100])}
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium mb-2">Sleep Score</h4>
                      <div className="h-[200px]">
                        {renderChart("sleep", "Sleep", CHART_COLORS.sleep, [40, 100])}
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium mb-2">Activity Score</h4>
                      <div className="h-[200px]">
                        {renderChart("activity", "Activity", CHART_COLORS.activity, [40, 100])}
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="activity" className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium mb-2">Daily Steps</h4>
                    <div className="h-[250px]">
                      {renderChart("steps", "Steps", CHART_COLORS.steps, [0, "auto"] as [number, number], true)}
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="heart" className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <h4 className="text-sm font-medium mb-2">HRV (Heart Rate Variability)</h4>
                      <div className="h-[200px]">
                        {renderChart("hrv", "HRV", CHART_COLORS.hrv)}
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium mb-2">Resting Heart Rate</h4>
                      <div className="h-[200px]">
                        {renderChart("rhr", "RHR", CHART_COLORS.rhr, [40, 100])}
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="sleep" className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <h4 className="text-sm font-medium mb-2">Sleep Score</h4>
                      <div className="h-[200px]">
                        {renderChart("sleep", "Sleep Score", CHART_COLORS.sleep, [40, 100])}
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium mb-2">Sleep Duration (hours)</h4>
                      <div className="h-[200px]">
                        {renderChart("sleep_hours", "Hours", CHART_COLORS.sleep_hours, [0, 12])}
                      </div>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
