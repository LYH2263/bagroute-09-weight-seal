export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    let msg = text || res.statusText;
    try {
      const data = JSON.parse(text);
      if (data && typeof data.detail === "string") msg = data.detail;
    } catch { /* keep raw text */ }
    throw new Error(msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
