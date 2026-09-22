import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; name: string; max_weight_kg: number; seal_weight_kg: number | null };
type Bag = { id: number; bag_index: number; weight_kg: number; volume_l: number; max_weight_kg: number; seal_weight_kg: number | null; items: { stop_name: string }[] };
export default function PackPage() {
  const [routes, setRoutes] = useState<R[]>([]);
  const [rid, setRid] = useState<number | "">("");
  const [bags, setBags] = useState<Bag[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { api<R[]>("/routes").then(r => { setRoutes(r); if (r[0]) setRid(r[0].id); }); }, []);

  const selected = routes.find(r => r.id === rid);

  async function run() {
    setMsg(""); setErr("");
    try {
      const out = await api<Bag[]>("/pack", { method: "POST", body: JSON.stringify({ route_id: rid }) });
      setBags(out);
      const seal = out[0]?.seal_weight_kg;
      setMsg(`完成装袋：${out.length} 袋 · 本次封袋阈值 ${seal == null ? "未启用" : `${seal}kg`}`);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>装袋</h2>
    <div className="toolbar">
      <select value={rid} onChange={e => { setRid(Number(e.target.value)); setBags([]); setMsg(""); setErr(""); }}>{routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
      <button onClick={run}>按路线顺序双约束装袋</button>
    </div>
    {selected && (
      <div className="seal-hint">
        当前路线封袋阈值：{selected.seal_weight_kg == null
          ? <span>未启用</span>
          : <span className="mono">{selected.seal_weight_kg}kg</span>}
        <span className="seal-hint-sub">（重量上限 {selected.max_weight_kg}kg；达到阈值后下一站开新袋）</span>
      </div>
    )}
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    {bags.map(b => (
      <div key={b.id}>
        <div className="mono">袋 {b.bag_index} · {b.weight_kg}kg / {b.volume_l}L
          {b.seal_weight_kg != null && (
            <span className="bag-threshold">阈值 {b.seal_weight_kg}kg / 上限 {b.max_weight_kg}kg</span>
          )}
        </div>
        <div className="bag-row">{b.items.map((it, i) => <div className="bag-block" key={i}>{it.stop_name}</div>)}</div>
      </div>
    ))}
  </>);
}
