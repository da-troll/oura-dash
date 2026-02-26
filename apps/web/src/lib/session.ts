/**
 * Session cookie helpers.
 * Extracted from route handlers for testability.
 */

/**
 * Get the session cookie name based on environment.
 * In production, uses __Host- prefix for additional security.
 */
export function getSessionCookieName(isProd: boolean): string {
  return isProd ? "__Host-session_token" : "session_token";
}

/**
 * Build cookie options for setting the session token.
 */
export function buildSessionCookie(
  token: string,
  isProd: boolean
): {
  name: string;
  value: string;
  options: {
    httpOnly: boolean;
    secure: boolean;
    sameSite: "lax";
    path: string;
    maxAge: number;
  };
} {
  return {
    name: getSessionCookieName(isProd),
    value: token,
    options: {
      httpOnly: true,
      secure: isProd,
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 30, // 30 days
    },
  };
}
