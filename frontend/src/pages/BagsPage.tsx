import { useEffect, useState } from "react";
import { api } from "../api/client";
type Bag = {
  id: number; route_id: number; bag_index: number; weight_kg: number; volume_l: number;
  seal_threshold_kg: number; max_weight_kg: number;
  items: { stop_name: string; weight_kg: number; volume_l: number }[];
};
export default function BagsPage() {
  const [rows, setRows] = useState<Bag[]>([]);
  useEffect(() => { api<Bag[]>("/bags").then(setRows); }, []);
  return (<>
    <h2>袋明细</h2>
    <table className="table"><thead><tr><th>路线</th><th>袋号</th><th>重量</th><th>封袋阈值</th><th>重量上限</th><th>体积</th><th>状态</th><th>订户</th></tr></thead>
    <tbody>{rows.map(b => {
      const sealed = b.weight_kg >= b.seal_threshold_kg - 1e-9;
      const overLimit = b.weight_kg > b.max_weight_kg + 1e-9;
      return <tr key={b.id}><td>{b.route_id}</td><td>{b.bag_index}</td>
        <td className="mono">{b.weight_kg}</td>
        <td className="mono">{b.seal_threshold_kg}</td>
        <td className="mono">{b.max_weight_kg}</td>
        <td className="mono">{b.volume_l}</td>
        <td>{overLimit ? <span className="err">超上限！</span> : sealed ? <span className="ok">达阈已封</span> : <span className="muted-note">未达阈</span>}</td>
        <td>{b.items.map(i => i.stop_name).join(" → ")}</td></tr>;
    })}
      {!rows.length && <tr><td colSpan={8}>尚无装袋结果，请先执行装袋</td></tr>}
    </tbody></table>
  </>);
}
