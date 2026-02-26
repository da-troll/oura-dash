/**
 * CSRF validation helper.
 * Extracted from route handlers for testability.
 */

/**
 * Validate that a CSRF token from a request header matches the cookie token.
 * Both must be present and equal.
 */
export function validateCsrfToken(
  headerToken: string | null | undefined,
  cookieToken: string | null | undefined
): boolean {
  return !!headerToken && !!cookieToken && headerToken === cookieToken;
}
