import { StoreEvent } from "../lib/useEventStream";

export default function LiveCount({ stats }: { stats: StoreEvent | null }) {
  const n = stats?.metadata?.live_count ?? 0;
  return (
    <div className="bg-panel border border-line rounded-xl p-4">
      <div className="text-xs uppercase tracking-wider text-slate-400">Live count</div>
      <div className="text-4xl font-semibold mt-2 text-accent">{n}</div>
      <div className="text-xs text-slate-500 mt-1">persons currently tracked</div>
    </div>
  );
}
