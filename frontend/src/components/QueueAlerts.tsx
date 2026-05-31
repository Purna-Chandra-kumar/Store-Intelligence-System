import { StoreEvent } from "../lib/useEventStream";

export default function QueueAlerts({ events }: { events: StoreEvent[] }) {
  const latest = events.find(e => e.event_type === "queue_detected");
  const n = latest?.metadata?.queue_length ?? 0;
  const wait = latest?.metadata?.wait_seconds ?? 0;
  return (
    <div className="bg-panel border border-line rounded-xl p-4">
      <div className="text-xs uppercase tracking-wider text-slate-400">Checkout queue</div>
      <div className="text-4xl font-semibold mt-2" style={{color: n>=5 ? "#ef4444" : n>=3 ? "#f59e0b" : "#10b981"}}>{n}</div>
      <div className="text-xs text-slate-500 mt-1">~{wait}s estimated wait</div>
    </div>
  );
}
