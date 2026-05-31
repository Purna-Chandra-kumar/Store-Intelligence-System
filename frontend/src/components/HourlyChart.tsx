import { useEffect, useState } from "react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from "recharts";
import { getJSON } from "../lib/api";

type Bucket = { bucket: string; count: number };

export default function HourlyChart() {
  const [data, setData] = useState<Bucket[]>([]);
  useEffect(() => {
    const load = () => getJSON<Bucket[]>("/analytics/hourly").then(setData).catch(()=>{});
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="h-44">
      <ResponsiveContainer>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="g" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.6}/>
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <XAxis dataKey="bucket" tickFormatter={(t)=>String(t).slice(11,16)}
                 stroke="#475569" fontSize={10}/>
          <YAxis stroke="#475569" fontSize={10}/>
          <Tooltip contentStyle={{background:"#0b0f17",border:"1px solid #1f2937"}}/>
          <Area type="monotone" dataKey="count" stroke="#22d3ee" fill="url(#g)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
