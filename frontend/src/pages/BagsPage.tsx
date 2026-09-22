import { useEffect, useState } from "react";
import { api } from "../api/client";
type Bag = { id: number; route_id: number; bag_index: number; weight_kg: number; volume_l: number; max_weight_kg: number; seal_weight_kg: number | null; items: { stop_name: string; weight_kg: number; volume_l: number }[] };
type R = { id: number; name: string };

const EPS = 1e-6;

export default function BagsPage() {
  const [rows, setRows] = useState<Bag[]>([]);
  const [routes, setRoutes] = useState<R[]>([]);
  useEffect(() => {
    api<Bag[]>("/bags").then(setRows);
    api<R[]>("/routes").then(setRoutes);
  }, []);
  const nameOf = (id: number) => routes.find(r => r.id === id)?.name ?? String(id);
  // 每条路线的最后一袋：末袋允许未满阈值
  const lastBagId = new Set<number>();
  rows.forEach((b, i) => {
    const next = rows[i + 1];
    if (!next || next.route_id !== b.route_id) lastBagId.add(b.id);
  });

  function verify(b: Bag): { text: string; cls: string } {
    const seal = b.seal_weight_kg;
    if (b.weight_kg > b.max_weight_kg + EPS) return { text: "超出重量上限", cls: "verify-bad" };
    if (seal == null) return { text: "未启用阈值", cls: "verify-muted" };
    const reached = b.weight_kg >= seal - EPS;
    if (b.items.length === 1 && b.weight_kg > seal + EPS) return { text: "单站独占（>阈值且≤上限）", cls: "verify-seal" };
    if (reached) return { text: "达到阈值即封", cls: "verify-seal" };
    if (lastBagId.has(b.id)) return { text: "末袋未满阈值", cls: "verify-muted" };
    return { text: "未满阈值（按上限分袋）", cls: "verify-muted" };
  }

  return (<>
    <h2>袋明细</h2>
    <p style={{ color: "var(--route-muted)", fontSize: ".82rem", marginTop: "-.35rem" }}>
      核验关系：封袋阈值 ≤ 袋重 ≤ 重量上限（达阈值即封）；单站自身大于阈值但小于上限时独占一袋。
    </p>
    <table className="table"><thead><tr><th>路线</th><th>袋号</th><th>封袋阈值</th><th>重量上限</th><th>袋重</th><th>体积</th><th>核验</th><th>订户</th></tr></thead>
      <tbody>{rows.map(b => {
        const v = verify(b);
        return (
          <tr key={b.id}>
            <td>{nameOf(b.route_id)}</td>
            <td>{b.bag_index}</td>
            <td className="mono">{b.seal_weight_kg == null ? "—" : b.seal_weight_kg}</td>
            <td className="mono">{b.max_weight_kg}</td>
            <td className="mono">{b.weight_kg}</td>
            <td className="mono">{b.volume_l}</td>
            <td><span className={`verify ${v.cls}`}>{v.text}</span></td>
            <td>{b.items.map(i => i.stop_name).join(" → ")}</td>
          </tr>
        );
      })}
        {!rows.length && <tr><td colSpan={8}>尚无装袋结果，请先执行装袋</td></tr>}
      </tbody></table>
  </>);
}
