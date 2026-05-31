import { useEffect, useMemo, useRef, useState } from "react";
import { API, getJSON } from "../lib/api";

type Camera = {
  id: string;
  name?: string;
  location?: string;
  live: boolean;
  meta?: { ts: number; count: number; w: number; h: number } | null;
  stream_url: string;
  snapshot_url: string;
};

type Props = {
  liveCount?: number;
};

/**
 * Live CCTV card.
 * Renders the backend MJPEG endpoint inside an <img> tag — the browser
 * decodes each multipart JPEG part natively, no JS frame loop required.
 */
export default function LiveStream({ liveCount }: Props) {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [activeId, setActiveId] = useState<string>("cam-01");
  const [nonce, setNonce] = useState<number>(() => Date.now());
  const [status, setStatus] = useState<"connecting" | "live" | "offline">("connecting");
  const imgRef = useRef<HTMLImageElement | null>(null);

  // Discover cameras + poll status
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await getJSON<{ cameras: Camera[] }>("/stream/cameras");
        if (cancelled) return;
        setCameras(r.cameras);
        if (r.cameras.length && !r.cameras.find((c) => c.id === activeId)) {
          setActiveId(r.cameras[0].id);
        }
      } catch {
        if (!cancelled) setStatus("offline");
      }
    };
    tick();
    const id = setInterval(tick, 5_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [activeId]);

  const streamSrc = useMemo(
    () => `${API}/stream/${activeId}?t=${nonce}`,
    [activeId, nonce],
  );

  const reconnect = () => {
    setStatus("connecting");
    setNonce(Date.now());
  };

  // Auto-reconnect if the MJPEG socket errors out
  useEffect(() => {
    setStatus("connecting");
    const el = imgRef.current;
    if (!el) return;
    const onLoad = () => setStatus("live");
    const onError = () => {
      setStatus("offline");
      const id = setTimeout(reconnect, 2_000);
      return () => clearTimeout(id);
    };
    el.addEventListener("load", onLoad);
    el.addEventListener("error", onError);
    return () => {
      el.removeEventListener("load", onLoad);
      el.removeEventListener("error", onError);
    };
  }, [streamSrc]);

  const active = cameras.find((c) => c.id === activeId);
  const dotColor =
    status === "live" ? "#10b981" : status === "connecting" ? "#f59e0b" : "#ef4444";

  return (
    <div className="bg-panel border border-line rounded-xl overflow-hidden flex flex-col">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-line">
        <span
          className="inline-block size-2 rounded-full animate-pulse"
          style={{ background: dotColor }}
        />
        <div className="text-sm font-medium tracking-tight">Live CCTV</div>
        <span className="text-[11px] uppercase tracking-wider text-slate-400">
          {status}
        </span>

        <div className="ml-auto flex items-center gap-2">
          {cameras.length > 1 && (
            <select
              value={activeId}
              onChange={(e) => setActiveId(e.target.value)}
              className="bg-black/30 border border-line rounded-md text-xs px-2 py-1 text-slate-200"
            >
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name ? `${c.id} · ${c.name}` : c.id}
                </option>
              ))}
            </select>
          )}
          <button
            onClick={reconnect}
            className="text-xs px-2 py-1 rounded-md border border-line text-slate-300 hover:bg-white/5"
          >
            Reconnect
          </button>
        </div>
      </div>

      <div className="relative bg-black aspect-video flex items-center justify-center">
        <img
          ref={imgRef}
          src={streamSrc}
          alt={`Live stream ${activeId}`}
          className="w-full h-full object-contain select-none"
          draggable={false}
        />
        {status !== "live" && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-xs text-slate-300 bg-black/60 px-3 py-1.5 rounded-md border border-line">
              {status === "connecting" ? "Connecting to camera…" : "Stream offline — retrying"}
            </div>
          </div>
        )}

        <div className="absolute left-3 top-3 flex items-center gap-2 text-[11px] font-mono px-2 py-1 rounded bg-black/50 border border-line">
          <span className="size-1.5 rounded-full bg-red-500" />
          REC · {activeId}
        </div>

        {typeof liveCount === "number" && (
          <div className="absolute right-3 top-3 text-[11px] font-mono px-2 py-1 rounded bg-black/50 border border-line">
            people: <span className="text-emerald-400">{liveCount}</span>
          </div>
        )}
      </div>

      <div className="px-4 py-2 text-[11px] text-slate-400 flex items-center justify-between">
        <span>
          {active?.location ?? "—"} · YOLOv8 + ByteTrack · server-rendered MJPEG
        </span>
        <a
          href={streamSrc}
          target="_blank"
          rel="noreferrer"
          className="hover:text-slate-200 underline-offset-2 hover:underline"
        >
          open raw
        </a>
      </div>
    </div>
  );
}
