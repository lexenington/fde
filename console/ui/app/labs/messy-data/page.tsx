"use client";

import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type Run = {
  run_id: string; finished_at: string; note: string; f1: number; precision: number; recall: number; passed: boolean;
  false_merge_pairs: number; missed_pairs: number; unassigned: number; unknown_count: number; multi_count: number;
  unknown_ids: string[]; in_multiple_clusters: string[]; junk_merged: string[]; clusters_truth: number; clusters_yours: number; records: number;
  false_merges?: { pair: Rec[] }[]; missed?: { pair: Rec[] }[];
};
type Rec = { id: string; row: Record<string, unknown> | null };
type State = { data_ready: boolean; clusters_found: boolean; clusters_path: string; target_f1: number; history: Run[] };

const fmt = (n: number) => n.toFixed(3);

function Pair({ pair }: { pair: Rec[] }) {
  return (
    <div className="card" style={{ padding: 10, fontSize: 13 }}>
      {pair.map((r) => (
        <div key={r.id} style={{ display: "flex", gap: 8, fontFamily: "ui-monospace, Menlo, monospace" }}>
          <strong style={{ minWidth: 110 }}>{r.id}</strong>
          <span style={{ overflowWrap: "anywhere" }}>{r.row ? Object.values(r.row).filter((v) => v !== "" && v !== null).join(" · ") : "(row not found in data/)"}</span>
        </div>
      ))}
    </div>
  );
}

export default function MessyData() {
  const [st, setSt] = useState<State | null>(null);
  const [res, setRes] = useState<Run | null>(null);
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = () => sim<State>("/labs/messy").then(setSt).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  async function score() {
    setBusy(true); setErr(null);
    try { setRes(await sim<Run>("/labs/messy/score", { json: { note } })); setNote(""); load(); }
    catch (e) { setErr((e as Error).message); }
    setBusy(false);
  }

  const hist = st?.history ?? [];
  const W = 520, H = 90;
  const pts = hist.map((h, i) => [hist.length < 2 ? W / 2 : (i / (hist.length - 1)) * (W - 20) + 10, H - 10 - h.f1 * (H - 20)]);
  const target = H - 10 - (st?.target_f1 ?? 0.92) * (H - 20);

  return (
    <>
      <h1>02/01 Messy data</h1>
      <p className="lede">
        Kumasi Fresh Foods has three exports and no shared ID. Write your clusters to <code>{st?.clusters_path ?? "out/clusters.json"}</code>,
        then score here. Each score is logged with a note, so by week 3 you have the record of what moved the number. For
        every wrong merge and every missed merge you see the raw rows: read a few before you touch the code.
      </p>
      {st && !st.data_ready && <div className="err">No data yet. In <code>02-technical-depth/01-messy-data/lab</code> run <code>python make_messy_data.py</code>.</div>}
      {err && <div className="err">{err}</div>}

      <div className="card" style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="What did you change since the last score? (e.g. lowercased emails)"
               style={{ flex: 1, minWidth: 260 }} onKeyDown={(e) => e.key === "Enter" && !busy && score()} />
        <button onClick={score} disabled={busy || !st?.data_ready}>{busy ? "Scoring…" : "Score my clusters"}</button>
      </div>

      {res && (
        <>
          <h2>Latest: F1 {fmt(res.f1)} <span className={`pill ${res.passed ? "pass" : "fail"}`}>{res.passed ? "target met" : `target ${st?.target_f1}`}</span></h2>
          <p>
            Precision <strong>{fmt(res.precision)}</strong> (of the pairs you merged, how many were right) · recall <strong>{fmt(res.recall)}</strong> (of
            the true pairs, how many you found) · {res.clusters_yours} clusters vs {res.clusters_truth} real customers.
            Which would you rather get wrong, the false merge or the miss? Your REPORT.md has to answer.
          </p>
          {(res.unassigned > 0 || res.unknown_count > 0 || res.multi_count > 0 || res.junk_merged.length > 0) && (
            <div className="err">
              {res.unassigned > 0 && <div>{res.unassigned} records are in no cluster (treated as singletons).</div>}
              {res.unknown_count > 0 && <div>{res.unknown_count} ids don&apos;t exist, e.g. {res.unknown_ids.join(", ")}.</div>}
              {res.multi_count > 0 && <div>{res.multi_count} records are in more than one cluster, e.g. {res.in_multiple_clusters.join(", ")}.</div>}
              {res.junk_merged.length > 0 && <div>Junk rows were merged into real customers: {res.junk_merged.join(", ")}.</div>}
            </div>
          )}
          <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
            <div>
              <h3>Wrong merges ({res.false_merge_pairs} pairs)</h3>
              {res.false_merges?.length ? res.false_merges.map((p, i) => <Pair key={i} pair={p.pair} />) : <p>None. Precision is perfect.</p>}
            </div>
            <div>
              <h3>Missed merges ({res.missed_pairs} pairs)</h3>
              {res.missed?.length ? res.missed.map((p, i) => <Pair key={i} pair={p.pair} />) : <p>None. Recall is perfect.</p>}
            </div>
          </div>
          <p style={{ color: "var(--muted)", fontSize: 13 }}>Six examples each, in order of id. Fix the pattern, not the instance, then score again.</p>
        </>
      )}

      {hist.length > 0 && (
        <>
          <h2>Score log</h2>
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: 560 }} role="img" aria-label="F1 over time">
            <line x1="0" x2={W} y1={target} y2={target} stroke="currentColor" strokeDasharray="4 4" opacity=".35" />
            <polyline fill="none" stroke="var(--accent)" strokeWidth="2" points={pts.map((p) => p.join(",")).join(" ")} />
            {pts.map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r="3" fill="var(--accent)" />)}
          </svg>
          <table>
            <thead><tr><th>When</th><th>F1</th><th>P</th><th>R</th><th>What changed</th></tr></thead>
            <tbody>
              {[...hist].reverse().map((h) => (
                <tr key={h.run_id}><td>{h.finished_at.replace("T", " ").replace("+00:00", "")}</td><td>{fmt(h.f1)}</td><td>{fmt(h.precision)}</td><td>{fmt(h.recall)}</td><td>{h.note || "—"}</td></tr>
              ))}
            </tbody>
          </table>
          <p style={{ color: "var(--muted)", fontSize: 13 }}>Saved in <code>02-technical-depth/01-messy-data/lab/runs/</code>. Commit it: it is the log of what moved the score.</p>
        </>
      )}
    </>
  );
}
