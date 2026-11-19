import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, setUnauthorizedHandler } from "@/lib/api";
import { jsonResponse } from "@/test/utils";

describe("api client", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    document.cookie = "persomy_csrf=tok123; path=/";
  });
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
    setUnauthorizedHandler(null);
  });

  it("n'envoie pas l'en-tête CSRF sur GET et utilise les cookies same-origin", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));
    await api("/dashboard/summary");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/dashboard/summary");
    expect(init.credentials).toBe("same-origin");
    expect(init.headers["X-CSRF-Token"]).toBeUndefined();
  });

  it("envoie l'en-tête CSRF sur POST avec un corps JSON", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));
    await api("/users", { method: "POST", body: { a: 1 } });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["X-CSRF-Token"]).toBe("tok123");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe('{"a":1}');
  });

  it("construit la query string sans valeurs vides", async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));
    await api("/users", { params: { search: "bob", role: "", active: undefined, limit: 10 } });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/users?search=bob&limit=10");
  });

  it("transforme une erreur API en ApiError", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: "login_throttled", message: "x" } }, 429, { "Retry-After": "120" }),
    );
    const err = await api("/auth/login", { method: "POST", body: {} }).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(429);
    expect(err.code).toBe("login_throttled");
    expect(err.retryAfter).toBe(120);
  });

  it("déclenche le gestionnaire de session expirée sur 401 de session", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "session_invalid", message: "x" } }, 401));
    await expect(api("/auth/me")).rejects.toBeInstanceOf(ApiError);
    expect(handler).toHaveBeenCalledOnce();
  });

  it("ne déclenche pas le gestionnaire pour un échec d'identifiants", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    fetchMock.mockResolvedValue(jsonResponse({ error: { code: "invalid_credentials", message: "x" } }, 401));
    await expect(api("/auth/login", { method: "POST", body: {} })).rejects.toBeInstanceOf(ApiError);
    expect(handler).not.toHaveBeenCalled();
  });

  it("gère 204 sans corps", async () => {
    fetchMock.mockResolvedValue(jsonResponse(null, 204));
    await expect(api("/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });
});
