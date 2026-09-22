import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; name: string; max_weight_kg: number; seal_threshold_kg: number };
type Bag = {
  id: number; bag_index: number; weight_kg: number; volume_l: number;
  seal_threshold_kg: number; max_weight_kg: number;
  items: { stop_name: string }[];
};
export default function PackPage() {
  const [routes, setRoutes] = useState<R[]>([]);
  const [rid, setRid] = useState<number | "">("");
  const [bags, setBags] = useState<Bag[]>([]);
  const [used, setUsed] = useState<{ threshold: number; max: number } | null>(null);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { api<R[]>("/routes").then(r => { setRoutes(r); if (r[0]) setRid(r[0].id); }); }, []);
  async function run() {
    setMsg(""); setErr(""); setUsed(null);
    try {
      const out = await api<Bag[]>("/pack", { method: "POST", body: JSON.stringify({ route_id: rid }) });
      setBags(out);
      const first = out[0];
      const route = routes.find(r => r.id === rid);
      if (first) setUsed({ threshold: first.seal_threshold_kg, max: first.max_weight_kg });
      else if (route) setUsed({ threshold: route.seal_threshold_kg, max: route.max_weight_kg });
      setMsg(`完成装袋：${out.length} 袋`);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>装袋</h2>
    <div className="toolbar">
      <select value={rid} onChange={e => setRid(Number(e.target.value))}>{routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
      <button onClick={run}>按路线顺序双约束装袋</button>
    </div>
    {msg && <div className="ok">{msg}</div>}
    {used && <div className="mono threshold-note">本次封袋阈值 {used.threshold}kg（重量上限 {used.max}kg）：袋重达阈值即封袋开新袋</div>}
    {err && <div className="err">{err}</div>}
    {bags.map(b => (
      <div key={b.id}>
        <div className="mono">袋 {b.bag_index} · {b.weight_kg}kg / {b.volume_l}L
          {b.weight_kg >= b.seal_threshold_kg - 1e-9 && <span className="sealed-tag">达阈已封</span>}
        </div>
        <div className="bag-row">{b.items.map((it, i) => <div className="bag-block" key={i}>{it.stop_name}</div>)}</div>
      </div>
    ))}
  </>);
}
