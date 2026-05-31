import { StoreEvent } from "../lib/useEventStream";

const COLORS: Record<string,string> = {
  person_entered:"#22d3ee", person_exited:"#64748b",
  zone_entered:"#a78bfa", zone_exited:"#64748b",
  queue_detected:"#f59e0b", crowd_detected:"#ef4444",
  loitering_detected:"#ef4444", anomaly_detected:"#ef4444",
  frame_stats:"#334155",
};

export default function EventFeed({ events }: { events: StoreEvent[] }) {
  return (
    <div className="bg-panel border border-line rounded-xl p-4">
      <div className="text-sm font-medium mb-3">Live event stream</div>
      <div className="space-y-1 max-h-[360px] overflow-auto pr-2">
        {events.slice(0, 80).map((e) => (
          <div key={e.event_id} className="flex items-center gap-2 text-xs">
            <span className="size-1.5 rounded-full" style={{background: COLORS[e.event_type] ?? "#475569"}} />
            <span className="text-slate-400 tabular-nums w-20">{e.timestamp.slice(11,19)}</span>
            <span className="font-mono text-slate-200">{e.event_type}</span>
            {e.zone && <span className="text-slate-500">· {e.zone}</span>}
            {e.track_id != null && <span className="text-slate-500">· #{e.track_id}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
