export const API = (import.meta.env.VITE_API_BASE as string) || "http://localhost:8000";
export const WS  = (import.meta.env.VITE_WS_URL  as string) || "ws://localhost:8000/ws/events";

export async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}
