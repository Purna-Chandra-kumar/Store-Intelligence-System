import { StoreEvent } from "../lib/useEventStream";

export default function ZonePanel({ stats }: { stats: StoreEvent | null }) {
  const occ = (stats?.metadata?.occupancy ?? {}) as Record<string, number>;
  const rows = Object.entries(occ);
  return (
    <div className="bg-panel border border-line rounded-xl p-4">
      <div className="text-sm font-medium mb-3">Zones</div>
      <div className="space-y-2">
        {rows.length === 0 && <div className="text-xs text-slate-500">Waiting for data…</div>}
        {rows.map(([id, n]) => (
          <div key={id} className="flex items-center justify-between">
            <span className="text-sm capitalize">{id}</span>
            <span className="text-sm tabular-nums text-accent">{n}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
