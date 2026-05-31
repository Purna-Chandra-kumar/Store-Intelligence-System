import { useEffect, useState } from "react";
import { getJSON } from "./lib/api";
import { useEventStream } from "./lib/useEventStream";
import LiveCount from "./components/LiveCount";
import ZonePanel from "./components/ZonePanel";
import EventFeed from "./components/EventFeed";
import HourlyChart from "./components/HourlyChart";
import Heatmap from "./components/Heatmap";
import AnomalyList from "./components/AnomalyList";
import QueueAlerts from "./components/QueueAlerts";
import LiveStream from "./components/LiveStream";

export default function App() {
  const { events, latestStats, connected } = useEventStream(400);
  const [summary, setSummary] = useState<string>("");

  useEffect(() => {
    const tick = async () => {
      try {
        const r = await getJSON<{ summary: string }>("/analytics/explain");
        setSummary(r.summary);
      } catch {}
    };
    tick();
    const id = setInterval(tick, 30_000);
    return () => clearInterval(id);
  }, []);

  const liveCount =
    (latestStats?.metadata as { live_count?: number } | undefined)?.live_count;

  return (
    <div className="min-h-full">
      <header className="border-b border-line bg-panel/60 backdrop-blur sticky top-0 z-10">
        <div className="max-w-[1400px] mx-auto px-6 py-3 flex items-center gap-4">
          <div
            className="size-2 rounded-full"
            style={{ background: connected ? "#10b981" : "#ef4444" }}
          />
          <h1 className="text-lg font-semibold tracking-tight">Store Intelligence</h1>
          <span className="text-xs text-slate-400">cam-01 · Main Floor</span>
          <div className="ml-auto text-xs text-slate-400 max-w-[60ch] truncate">
            {summary}
          </div>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto p-6 grid grid-cols-12 gap-6">
        <section className="col-span-12 lg:col-span-8 grid grid-cols-3 gap-4">
          <LiveCount stats={latestStats} />
          <QueueAlerts events={events} />
          <div className="col-span-1 bg-panel border border-line rounded-xl p-4">
            <div className="text-xs uppercase tracking-wider text-slate-400">
              Events / min
            </div>
            <div className="text-3xl font-semibold mt-2">{events.length}</div>
            <div className="text-xs text-slate-500 mt-1">rolling buffer</div>
          </div>

          <div className="col-span-3">
            <LiveStream liveCount={liveCount} />
          </div>

          <div className="col-span-3 bg-panel border border-line rounded-xl p-4">
            <div className="text-sm font-medium mb-3">Hourly footfall (last 24h)</div>
            <HourlyChart />
          </div>

          <div className="col-span-3 bg-panel border border-line rounded-xl p-4">
            <div className="text-sm font-medium mb-3">Floor heatmap</div>
            <Heatmap stats={latestStats} />
          </div>
        </section>

        <aside className="col-span-12 lg:col-span-4 space-y-4">
          <ZonePanel stats={latestStats} />
          <AnomalyList events={events} />
          <EventFeed events={events} />
        </aside>
      </main>
    </div>
  );
}
