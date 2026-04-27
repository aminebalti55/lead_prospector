const BASE = "/api";

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `API Error: ${res.status}`);
  }
  return res.json();
}

export function downloadUrl(filename: string): string {
  return `${BASE}/cold/files/${encodeURIComponent(filename)}/download`;
}
