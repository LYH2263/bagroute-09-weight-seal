import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; name: string; max_weight_kg: number; max_volume_l: number; seal_weight_kg: number | null };
export default function RoutesPage() {
  const [rows, setRows] = useState<R[]>([]);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const [savingId, setSavingId] = useState<number | null>(null);

  async function load() {
    const rs = await api<R[]>("/routes");
    setRows(rs);
    setDrafts(Object.fromEntries(rs.map(r => [r.id, r.seal_weight_kg == null ? "" : String(r.seal_weight_kg)])));
  }
  useEffect(() => { load(); }, []);

  async function save(r: R) {
    setMsg(""); setErr("");
    const raw = (drafts[r.id] ?? "").trim();
    // 空串视为不启用阈值
    if (raw === "") {
      setSavingId(r.id);
      try {
        const updated = await api<R>(`/routes/${r.id}`, { method: "PUT", body: JSON.stringify({ seal_weight_kg: null }) });
        setRows(prev => prev.map(x => x.id === r.id ? updated : x));
        setMsg(`已清除「${r.name}」的封袋阈值`);
      } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
      finally { setSavingId(null); }
      return;
    }
    const v = Number(raw);
    if (!Number.isFinite(v) || v <= 0) {
      setErr("封袋阈值必须是大于 0 的数字");
      return;
    }
    // 阈值不得大于重量上限：前端先拦截，后端也会拒绝
    if (v > r.max_weight_kg) {
      setErr(`提交失败：封袋阈值 ${v}kg 不得大于重量上限 ${r.max_weight_kg}kg（${r.name}）`);
      return;
    }
    setSavingId(r.id);
    try {
      const updated = await api<R>(`/routes/${r.id}`, { method: "PUT", body: JSON.stringify({ seal_weight_kg: v }) });
      setRows(prev => prev.map(x => x.id === r.id ? updated : x));
      setMsg(`「${r.name}」封袋阈值已保存为 ${v}kg`);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setSavingId(null); }
  }

  return (<>
    <h2>路线</h2>
    <p style={{ color: "var(--route-muted)", fontSize: ".82rem", marginTop: "-.35rem" }}>
      封袋阈值 ≤ 重量上限；当前袋装到阈值后，下一站必须开新袋（留空表示不启用）。
    </p>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table">
      <thead><tr><th>名称</th><th>重量上限 kg</th><th>体积上限 L</th><th>封袋阈值 kg</th><th></th></tr></thead>
      <tbody>{rows.map(r => {
        const draft = drafts[r.id] ?? "";
        const v = Number(draft);
        const illegal = draft.trim() !== "" && (!Number.isFinite(v) || v <= 0 || v > r.max_weight_kg);
        return (
          <tr key={r.id}>
            <td>{r.name}</td>
            <td className="mono">{r.max_weight_kg}</td>
            <td className="mono">{r.max_volume_l}</td>
            <td>
              <input
                style={{ width: 110, borderColor: illegal ? "var(--reject)" : undefined }}
                type="number" step="0.1" min="0" max={r.max_weight_kg}
                placeholder="不启用"
                value={draft}
                onChange={e => setDrafts(prev => ({ ...prev, [r.id]: e.target.value }))}
              />
              {illegal && <div className="err" style={{ fontSize: ".72rem" }}>需 ≤ {r.max_weight_kg}</div>}
            </td>
            <td><button disabled={savingId === r.id} onClick={() => save(r)}>
              {savingId === r.id ? "保存中…" : "保存"}
            </button></td>
          </tr>
        );
      })}</tbody>
    </table>
  </>);
}
