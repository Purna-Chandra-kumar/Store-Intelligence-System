import { StoreEvent } from "../lib/useEventStream";

export default function AnomalyList({ events }: { events: StoreEvent[] }) {
  const anomalies = events.filter(e => e.event_type.endsWith("_detected") && e.event_type !== "queue_detected").slice(0, 12);
  return (
    <div className="bg-panel border border-line rounded-xl p-4">
      <div className="text-sm font-medium mb-3">Anomalies</div>
      {anomalies.length === 0 && <div className="text-xs text-slate-500">No anomalies in window.</div>}
      <div className="space-y-2">
        {anomalies.map(a => (
          <div key={a.event_id} className="text-xs border-l-2 border-danger pl-2">
            <div className="text-slate-200">{a.metadata?.detail ?? a.event_type}</div>
            <div className="text-slate-500">{a.timestamp.slice(11,19)} · {a.zone ?? "global"}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
