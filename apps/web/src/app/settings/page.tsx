"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

interface AuthStatus {
  connected: boolean;
  expiresAt?: string;
  scopes?: string[];
}

interface SyncResult {
  status: string;
  daysProcessed?: number;
  message?: string;
}

function SettingsContent() {
  const searchParams = useSearchParams();
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Date range for backfill
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return date.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split("T")[0];
  });

  // Check for OAuth callback results
  useEffect(() => {
    const success = searchParams.get("success");
    const errorParam = searchParams.get("error");

    if (success === "connected") {
      setSyncResult({ status: "success", message: "Connected to Oura!" });
    } else if (errorParam) {
      setError(`OAuth error: ${errorParam}`);
    }
  }, [searchParams]);

  // Fetch auth status
  useEffect(() => {
    async function fetchAuthStatus() {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_ANALYTICS_URL || "http://localhost:8001"}/auth/status`
        );
        const data = await response.json();
        setAuthStatus(data);
      } catch (err) {
        console.error("Failed to fetch auth status:", err);
        setError("Failed to connect to analytics service");
      } finally {
        setLoading(false);
      }
    }

    fetchAuthStatus();
  }, []);

  const handleConnect = () => {
    window.location.href = "/api/oura/auth";
  };

  const handleDisconnect = async () => {
    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_ANALYTICS_URL || "http://localhost:8001"}/auth/revoke`,
        { method: "POST" }
      );
      setAuthStatus({ connected: false });
      setSyncResult({ status: "success", message: "Disconnected from Oura" });
    } catch (err) {
      setError("Failed to disconnect");
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    setError(null);

    try {
      // Run ingestion
      const ingestResponse = await fetch(
        `${process.env.NEXT_PUBLIC_ANALYTICS_URL || "http://localhost:8001"}/admin/ingest?start=${startDate}&end=${endDate}`,
        { method: "POST" }
      );

      if (!ingestResponse.ok) {
        throw new Error("Ingestion failed");
      }

      const ingestResult = await ingestResponse.json();

      // Run feature computation
      const featuresResponse = await fetch(
        `${process.env.NEXT_PUBLIC_ANALYTICS_URL || "http://localhost:8001"}/admin/features?start=${startDate}&end=${endDate}`,
        { method: "POST" }
      );

      if (!featuresResponse.ok) {
        throw new Error("Feature computation failed");
      }

      const featuresResult = await featuresResponse.json();

      setSyncResult({
        status: "completed",
        daysProcessed: ingestResult.daysProcessed,
        message: `${ingestResult.message}. ${featuresResult.message}`,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto py-8">
        <div className="animate-pulse">Loading...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Settings</h1>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link href="/dashboard">
            <Button variant="outline">Dashboard</Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {syncResult && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          {syncResult.message}
        </div>
      )}

      {/* Connection Status */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Oura Connection
            {authStatus?.connected ? (
              <Badge variant="default">Connected</Badge>
            ) : (
              <Badge variant="secondary">Not Connected</Badge>
            )}
          </CardTitle>
          <CardDescription>
            Connect your Oura Ring to sync your health data
          </CardDescription>
        </CardHeader>
        <CardContent>
          {authStatus?.connected ? (
            <div className="space-y-4">
              {authStatus.expiresAt && (
                <p className="text-sm text-muted-foreground">
                  Token expires: {new Date(authStatus.expiresAt).toLocaleString()}
                </p>
              )}
              {authStatus.scopes && authStatus.scopes.length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Scopes:</p>
                  <div className="flex flex-wrap gap-1">
                    {authStatus.scopes.map((scope) => (
                      <Badge key={scope} variant="outline" className="text-xs">
                        {scope}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              <Button variant="destructive" onClick={handleDisconnect}>
                Disconnect
              </Button>
            </div>
          ) : (
            <Button onClick={handleConnect}>Connect Oura</Button>
          )}
        </CardContent>
      </Card>

      {/* Data Sync */}
      {authStatus?.connected && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Data Sync</CardTitle>
            <CardDescription>
              Fetch and process your Oura data for analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  End Date
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
            </div>
            <Button onClick={handleSync} disabled={syncing}>
              {syncing ? "Syncing..." : "Sync Data"}
            </Button>
          </CardContent>
        </Card>
      )}

      <Separator className="my-6" />

      {/* Navigation */}
      <div className="space-y-2">
        <h2 className="text-lg font-semibold mb-2">Quick Links</h2>
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard">
            <Button variant="outline">Dashboard</Button>
          </Link>
          <Link href="/insights">
            <Button variant="outline">Insights</Button>
          </Link>
          <Link href="/correlations">
            <Button variant="outline">Correlations</Button>
          </Link>
          <Link href="/patterns">
            <Button variant="outline">Patterns</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="container mx-auto py-8"><div className="animate-pulse">Loading...</div></div>}>
      <SettingsContent />
    </Suspense>
  );
}
