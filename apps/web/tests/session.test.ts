import { describe, it, expect } from "vitest";
import { getSessionCookieName, buildSessionCookie } from "@/lib/session";

describe("getSessionCookieName", () => {
  it("returns __Host-session_token in production", () => {
    expect(getSessionCookieName(true)).toBe("__Host-session_token");
  });

  it("returns session_token in development", () => {
    expect(getSessionCookieName(false)).toBe("session_token");
  });
});

describe("buildSessionCookie", () => {
  it("builds production cookie with secure flag", () => {
    const cookie = buildSessionCookie("my-token", true);
    expect(cookie.name).toBe("__Host-session_token");
    expect(cookie.value).toBe("my-token");
    expect(cookie.options.httpOnly).toBe(true);
    expect(cookie.options.secure).toBe(true);
    expect(cookie.options.sameSite).toBe("lax");
    expect(cookie.options.path).toBe("/");
    expect(cookie.options.maxAge).toBe(60 * 60 * 24 * 30);
  });

  it("builds development cookie without secure flag", () => {
    const cookie = buildSessionCookie("dev-token", false);
    expect(cookie.name).toBe("session_token");
    expect(cookie.value).toBe("dev-token");
    expect(cookie.options.httpOnly).toBe(true);
    expect(cookie.options.secure).toBe(false);
    expect(cookie.options.sameSite).toBe("lax");
  });
});
