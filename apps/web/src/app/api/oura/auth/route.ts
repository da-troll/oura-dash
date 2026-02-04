import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { getAuthUrl } from "@/lib/api-client";

/**
 * GET /api/oura/auth
 *
 * Initiates the OAuth flow by redirecting to Oura's authorization page.
 * Stores the state in a cookie for CSRF verification in the callback.
 */
export async function GET() {
  try {
    // Get auth URL and state from analytics service
    const { url, state } = await getAuthUrl();

    // Store state in an HTTP-only cookie for CSRF verification
    const cookieStore = await cookies();
    cookieStore.set("oura_oauth_state", state, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 600, // 10 minutes
      path: "/",
    });

    // Redirect to Oura authorization URL
    return NextResponse.redirect(url);
  } catch (error) {
    console.error("Failed to initiate OAuth:", error);
    return NextResponse.redirect(
      new URL("/settings?error=auth_init_failed", process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000")
    );
  }
}
