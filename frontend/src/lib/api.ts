const CSRF_COOKIE = "persomy_csrf";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export class ApiError extends Error {
  status: number;
  code: string;
  retryAfter: number | null;

  constructor(status: number, code: string, message: string, retryAfter: number | null = null) {
    super(message);
    this.status = status;
    this.code = code;
    this.retryAfter = retryAfter;
  }
}

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=")[1]) : null;
}

export async function api<T = void>(
  path: string,
  options: { method?: string; body?: unknown; params?: Record<string, string | number | boolean | undefined | null> } = {},
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (!SAFE_METHODS.has(method)) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  let url = `/api/v1${path}`;
  if (options.params) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(options.params)) {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    }
    const s = qs.toString();
    if (s) url += `?${s}`;
  }

  const response = await fetch(url, {
    method,
    headers,
    credentials: "same-origin",
    cache: "no-store",
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 204) return undefined as T;

  let payload: any = null;
  try {
    payload = await response.json();
  } catch {
    /* corps non JSON */
  }

  if (!response.ok) {
    const code: string = payload?.error?.code ?? "unknown";
    const message: string = payload?.error?.message ?? response.statusText;
    const retry = response.headers.get("Retry-After");
    if (response.status === 401 && (code === "not_authenticated" || code === "session_invalid")) {
      unauthorizedHandler?.();
    }
    throw new ApiError(response.status, code, message, retry ? Number(retry) : null);
  }
  return payload as T;
}
