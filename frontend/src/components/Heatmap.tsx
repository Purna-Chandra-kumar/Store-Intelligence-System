import { StoreEvent } from "../lib/useEventStream";

export default function Heatmap({ stats }: { stats: StoreEvent | null }) {
  const hm = stats?.metadata?.heatmap;
  if (!hm) return <div className="text-xs text-slate-500">Waiting for heatmap…</div>;
  const { cols, rows, values } = hm as { cols: number; rows: number; values: number[] };
  const max = Math.max(1, ...values);
  return (
    <div className="grid gap-px bg-line p-px rounded"
         style={{gridTemplateColumns:`repeat(${cols},1fr)`, aspectRatio: `${cols}/${rows}`}}>
      {values.map((v,i)=>{
        const a = Math.min(1, v / max);
        return <div key={i} style={{background:`rgba(34,211,238,${a})`}} />;
      })}
    </div>
  );
}
