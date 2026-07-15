// FastAPI-Backend hinter dem Next.js-Rewrite; lokal ebenfalls via /api.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export class ApiError extends Error {}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    // FastAPI liefert Fehler als { detail: "..." }
    let detail = `Anfrage fehlgeschlagen (${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // Body nicht lesbar/kein JSON — Default-Meldung behalten
    }
    throw new ApiError(detail);
  }
  return res.json() as Promise<T>;
}

export function apiUrl(path: string): string {
  return `${API_URL}${path}`;
}

export async function apiGet<T>(path: string): Promise<T> {
  return handle<T>(await fetch(apiUrl(path), { cache: "no-store" }));
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  return handle<T>(await fetch(apiUrl(path), { method: "POST", body: form }));
}

export async function apiPost<T>(path: string): Promise<T> {
  return handle<T>(await fetch(apiUrl(path), { method: "POST" }));
}
