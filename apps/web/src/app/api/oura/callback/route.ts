import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

import { exchangeCode } from "@/lib/api-client";

/**
 * GET /api/oura/callback
 *
 * Handles the OAuth callback from Oura.
 * Verifies the state, forwards the code to the analytics service,
 * and redirects to the settings page.
 */
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");

  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000";

  // Handle OAuth errors from Oura
  if (error) {
    console.error("OAuth error from Oura:", error);
    return NextResponse.redirect(
      new URL(`/settings?error=${encodeURIComponent(error)}`, baseUrl)
    );
  }

  // Verify code is present
  if (!code) {
    console.error("No code in OAuth callback");
    return NextResponse.redirect(
      new URL("/settings?error=missing_code", baseUrl)
    );
  }

  // Verify state matches the one we stored
  const cookieStore = await cookies();
  const storedState = cookieStore.get("oura_oauth_state")?.value;

  if (!storedState || storedState !== state) {
    console.error("State mismatch in OAuth callback");
    return NextResponse.redirect(
      new URL("/settings?error=state_mismatch", baseUrl)
    );
  }

  // Clear the state cookie
  cookieStore.delete("oura_oauth_state");

  try {
    // Forward code to analytics service for token exchange
    const response = await exchangeCode(code);

    if (!response.success) {
      console.error("Token exchange failed:", response.message);
      return NextResponse.redirect(
        new URL(`/settings?error=${encodeURIComponent(response.message || "exchange_failed")}`, baseUrl)
      );
    }

    // Success - redirect to settings with success flag
    return NextResponse.redirect(
      new URL("/settings?success=connected", baseUrl)
    );
  } catch (error) {
    console.error("Failed to exchange OAuth code:", error);
    return NextResponse.redirect(
      new URL("/settings?error=exchange_failed", baseUrl)
    );
  }
}
