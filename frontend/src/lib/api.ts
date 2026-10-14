/**
 * Small fetch wrapper for the LKMS API.
 *
 * The access token lives only in memory. The refresh token is kept in
 * sessionStorage so a reload keeps staff signed in, but closing the tab
 * signs them out.
 */

const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const REFRESH_KEY = "lkms.refresh";

/** Full URL of an API path, for <img src> and links. */
export const apiUrl = (path: string) => `${BASE}${path}`;

export class ApiError extends Error {
  constructor(
    public status: number,
    public data: unknown,
  ) {
    super(describeError(data) || `Request failed (${status})`);
  }

  /** Field-level messages, e.g. { father_phone: ["Enter a 10-digit ..."] } */
  get fieldErrors(): Record<string, string[]> {
    if (this.data && typeof this.data === "object" && !Array.isArray(this.data)) {
      const out: Record<string, string[]> = {};
      for (const [key, value] of Object.entries(this.data as Record<string, unknown>)) {
        if (key === "detail" || key === "non_field_errors") continue;
        out[key] = Array.isArray(value) ? value.map(String) : [String(value)];
      }
      return out;
    }
    return {};
  }
}

function describeError(data: unknown): string {
  if (!data) return "";
  if (typeof data === "string") return data;
  if (Array.isArray(data)) return data.map(describeError).join(" ");
  if (typeof data === "object") {
    const obj = data as Record<string, unknown>;
    if (obj.detail) return describeError(obj.detail);
    if (obj.non_field_errors) return describeError(obj.non_field_errors);
    return Object.values(obj).map(describeError).filter(Boolean).join(" ");
  }
  return String(data);
}

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
let onSignedOut: () => void = () => {};

function readRefresh(): string | null {
  try {
    return sessionStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

function writeRefresh(token: string | null) {
  try {
    if (token) sessionStorage.setItem(REFRESH_KEY, token);
    else sessionStorage.removeItem(REFRESH_KEY);
  } catch {
    /* storage unavailable: stay signed in for this page only */
  }
}

export const tokens = {
  set(access: string, refresh: string) {
    accessToken = access;
    writeRefresh(refresh);
  },
  clear() {
    accessToken = null;
    writeRefresh(null);
  },
  hasRefresh: () => Boolean(readRefresh()),
  refresh: () => readRefresh(),
  onSignedOut(callback: () => void) {
    onSignedOut = callback;
  },
};

async function refreshAccess(): Promise<boolean> {
  const refresh = readRefresh();
  if (!refresh) return false;
  refreshing ??= (async () => {
    const response = await fetch(`${BASE}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!response.ok) {
      tokens.clear();
      onSignedOut();
      return false;
    }
    const data = await response.json();
    tokens.set(data.access, data.refresh ?? refresh);
    return true;
  })().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | undefined | null>;
  headers?: Record<string, string>;
  auth?: boolean;
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }
  const headers: Record<string, string> = { Accept: "application/json", ...options.headers };
  let body: BodyInit | undefined;
  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  if (options.auth !== false && accessToken) headers.Authorization = `Bearer ${accessToken}`;
  return fetch(url, { method: options.method ?? "GET", headers, body });
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await send(path, options);
  if (response.status === 401 && options.auth !== false && (await refreshAccess())) {
    response = await send(path, options);
  }
  if (!response.ok) {
    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      /* not JSON */
    }
    throw new ApiError(response.status, data);
  }
  if (response.status === 204 || response.status === 205) return undefined as T;
  return response.json() as Promise<T>;
}

/** Fetch a protected file (document, photo) and return an object URL for viewing. */
export async function fetchFileUrl(path: string): Promise<string> {
  let response = await send(path, {});
  if (response.status === 401 && (await refreshAccess())) response = await send(path, {});
  if (!response.ok) throw new ApiError(response.status, null);
  return URL.createObjectURL(await response.blob());
}

export const api = {
  get: <T>(path: string, query?: RequestOptions["query"]) => request<T>(path, { query }),
  post: <T>(path: string, body?: unknown, extra: Partial<RequestOptions> = {}) =>
    request<T>(path, { method: "POST", body, ...extra }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: "PATCH", body }),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: "PUT", body }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
  refreshAccess,
};
