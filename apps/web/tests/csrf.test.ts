import { describe, it, expect } from "vitest";
import { validateCsrfToken } from "@/lib/csrf";

describe("validateCsrfToken", () => {
  it("returns true when header and cookie tokens match", () => {
    expect(validateCsrfToken("abc123", "abc123")).toBe(true);
  });

  it("returns false when tokens do not match", () => {
    expect(validateCsrfToken("abc123", "xyz789")).toBe(false);
  });

  it("returns false when header token is null", () => {
    expect(validateCsrfToken(null, "abc123")).toBe(false);
  });

  it("returns false when cookie token is null", () => {
    expect(validateCsrfToken("abc123", null)).toBe(false);
  });

  it("returns false when header token is undefined", () => {
    expect(validateCsrfToken(undefined, "abc123")).toBe(false);
  });

  it("returns false when cookie token is undefined", () => {
    expect(validateCsrfToken("abc123", undefined)).toBe(false);
  });

  it("returns false when both tokens are empty strings", () => {
    expect(validateCsrfToken("", "")).toBe(false);
  });

  it("returns false when header is empty string", () => {
    expect(validateCsrfToken("", "abc123")).toBe(false);
  });

  it("returns false when both are null", () => {
    expect(validateCsrfToken(null, null)).toBe(false);
  });
});
