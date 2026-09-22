import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; name: string; max_weight_kg: number; max_volume_l: number; seal_threshold_kg: number };
export default function RoutesPage() {
  const [rows, setRows] = useState<R[]>([]);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [errs, setErrs] = useState<Record<number, string>>({});
  const [oks, setOks] = useState<Record<number, string>>({});
  useEffect(() => {
    api<R[]>("/routes").then(rs => {
      setRows(rs);
      setDrafts(Object.fromEntries(rs.map(r => [r.id, String(r.seal_threshold_kg)])));
    });
  }, []);
  async function save(r: R) {
    setErrs(e => ({ ...e, [r.id]: "" }));
    setOks(o => ({ ...o, [r.id]: "" }));
    const v = Number(drafts[r.id]);
    if (!Number.isFinite(v) || v <= 0) {
      setErrs(e => ({ ...e, [r.id]: "封袋阈值必须大于 0" }));
      return;
    }
    try {
      const out = await api<R>(`/routes/${r.id}`, {
        method: "PATCH",
        body: JSON.stringify({ seal_threshold_kg: v }),
      });
      setRows(rs => rs.map(x => (x.id === r.id ? out : x)));
      setDrafts(d => ({ ...d, [r.id]: String(out.seal_threshold_kg) }));
      setOks(o => ({ ...o, [r.id]: "已保存" }));
    } catch (e) {
      setErrs(er => ({ ...er, [r.id]: e instanceof Error ? e.message : String(e) }));
    }
  }
  return (<>
    <h2>路线</h2>
    <table className="table"><thead><tr><th>名称</th><th>重量上限 kg</th><th>体积上限 L</th><th>封袋阈值 kg</th><th></th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.id}>
      <td>{r.name}</td><td className="mono">{r.max_weight_kg}</td><td className="mono">{r.max_volume_l}</td>
      <td>
        <input
          className="mono threshold-input"
          type="number" min="0" step="0.1" max={r.max_weight_kg}
          value={drafts[r.id] ?? ""}
          onChange={e => setDrafts(d => ({ ...d, [r.id]: e.target.value }))}
        />
        {errs[r.id] && <div className="err">{errs[r.id]}</div>}
        {oks[r.id] && <div className="ok">{oks[r.id]}</div>}
      </td>
      <td><button onClick={() => save(r)}>保存阈值</button></td>
    </tr>)}</tbody></table>
    <p className="muted-note">袋重达到封袋阈值即封袋开新袋；阈值不得大于重量上限。</p>
  </>);
}
