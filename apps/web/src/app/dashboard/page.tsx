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
  ReferenceLine,
} from "recharts";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface DashboardSummary {
  readiness_avg: number | null;
  sleep_avg: number | null;
  activity_avg: number | null;
  steps_avg: number | null;
  days_with_data: number;
}

interface TrendPoint {
  date: string;
  value: number | null;
  baseline: number | null;
}

interface DashboardData {
  connected: boolean;
  summary: DashboardSummary;
  readiness_trend: TrendPoint[];
}

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

  const chartData = data?.readiness_trend.map((point) => ({
    date: point.date.slice(5), // MM-DD format
    value: point.value,
    baseline: point.baseline,
  }));

  const hasData = data?.connected && data.summary.days_with_data > 0;

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Link href="/settings">
          <Button variant="outline">Settings</Button>
        </Link>
      </div>

      {loading && (
        <div className="text-center text-muted-foreground py-12">
          Loading...
        </div>
      )}

      {error && (
        <div className="text-center text-red-500 py-12">
          Error: {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Readiness Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatValue(data?.summary.readiness_avg)}
                </div>
                <p className="text-xs text-muted-foreground">7-day average</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Sleep Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatValue(data?.summary.sleep_avg)}
                </div>
                <p className="text-xs text-muted-foreground">7-day average</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Activity Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatValue(data?.summary.activity_avg)}
                </div>
                <p className="text-xs text-muted-foreground">7-day average</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Daily Steps</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatValue(data?.summary.steps_avg)}
                </div>
                <p className="text-xs text-muted-foreground">7-day average</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Readiness Trend</CardTitle>
              <CardDescription>
                Your readiness score over time with 28-day baseline
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              {hasData && chartData && chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      interval="preserveStartEnd"
                    />
                    <YAxis domain={[40, 100]} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <ReferenceLine y={70} stroke="#888" strokeDasharray="3 3" />
                    <Line
                      type="monotone"
                      dataKey="baseline"
                      stroke="#94a3b8"
                      strokeDasharray="5 5"
                      dot={false}
                      name="28-day avg"
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#2563eb"
                      strokeWidth={2}
                      dot={{ fill: "#2563eb", r: 3 }}
                      name="Readiness"
                      connectNulls={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  <div className="text-center">
                    <p>Connect your Oura Ring and sync data to see trends</p>
                    <Link href="/settings" className="mt-2 inline-block">
                      <Button variant="link">Go to Settings</Button>
                    </Link>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
