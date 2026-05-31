import { useEffect, useRef, useState } from "react";
import { WS } from "./api";

export type StoreEvent = {
  event_id: string;
  event_type: string;
  timestamp: string;
  camera_id: string;
  track_id?: number | null;
  zone?: string | null;
  metadata: Record<string, any>;
};

/** Subscribes to the backend WS event stream with auto-reconnect. */
export function useEventStream(maxBuffer = 200) {
  const [events, setEvents] = useState<StoreEvent[]>([]);
  const [latestStats, setLatestStats] = useState<StoreEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let stop = false;
    const connect = () => {
      const ws = new WebSocket(WS);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!stop) setTimeout(connect, 1500);
      };
      ws.onmessage = (m) => {
        try {
          const ev = JSON.parse(m.data) as StoreEvent;
          if (ev.event_type === "frame_stats") setLatestStats(ev);
          setEvents((prev) => [ev, ...prev].slice(0, maxBuffer));
        } catch {}
      };
    };
    connect();
    return () => { stop = true; wsRef.current?.close(); };
  }, [maxBuffer]);

  return { events, latestStats, connected };
}
