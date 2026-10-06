"use client";

import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type Summary = Record<string, number | null | Record<string, number>>;
type RunRow = { id: string; model: string; summary: Summary };
type Failure = { doc: string; error?: string; bad?: { field: string; got: unknown; want: unknown }[]; not_flagged?: boolean; why?: string; confidence?: number; text?: string };
type Route = { threshold: number; auto: number; auto_pct: number; wrong_on_auto: number; error_rate_on_auto: number | null; leaked: number; cost_per_doc?: number };
type Detail = {
  id: string; model: string; summary: Summary; failures: Failure[]; compare_to: string | null;
  deltas: Record<string, { was: number; now: number; better: boolean }>; regressions: string[]; fixed: string[]; routing: Route[];
};

const COLS: [string, string][] = [["doc_accuracy", "Doc acc."], ["review_recall", "Review recall"], ["false_flag_rate", "False flags"], ["auto_processed_pct", "Auto %"],
  ["error_rate_on_auto", "Err on auto"], ["latency_p50_s", "p50 s"], ["cost_per_1000_docs_usd", "$/1000"]];
const show = (v: unknown) => (typeof v === "number" ? String(v) : "–");

export default function AiLab() {
  const [runs, setRuns] = useState<RunRow[] | null>(null);
  const [path, setPath] = useState("");
  const [sel, setSel] = useState<string | null>(null);
  const [d, setD] = useState<Detail | null>(null);
  const [wrong, setWrong] = useState("");
  const [review, setReview] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = () => sim<{ runs: RunRow[]; lab_path: string }>("/labs/ai").then((x) => { setRuns(x.runs); setPath(x.lab_path); if (x.runs.length && !sel) setSel(x.runs[x.runs.length - 1].id); }).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!sel || !runs) return;
    const i = runs.findIndex((r) => r.id === sel);
    const q = new URLSearchParams();
    if (i > 0) q.set("compare", runs[i - 1].id);
    if (wrong && review) { q.set("wrong_cost", wrong); q.set("review_cost", review); }
    sim<Detail>(`/labs/ai/runs/${sel}?${q}`).then(setD).catch((e) => setErr(e.message));
  }, [sel, runs, wrong, review]);

  return (
    <>
      <h1>02/03 AI engineering</h1>
      <p className="lede">
        Run <code>python eval.py</code> in <code>{path || "02-technical-depth/03-ai-engineering/lab"}</code> (your key, on your machine). This page
        reads the runs it saves: the metrics over time, what changed against the previous run, every failing document next to its text and its gold
        answer, and the review table priced in cedis. Read every failure before you change anything.
      </p>
      {err && <div className="err">{err}</div>}
      {runs && runs.length === 0 && <div className="err">No runs yet. Run <code>python eval.py</code> for your baseline.</div>}

      {runs && runs.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr><th>Run</th>{COLS.map(([, l]) => <th key={l}>{l}</th>)}</tr></thead>
            <tbody>
              {[...runs].reverse().map((r) => (
                <tr key={r.id} onClick={() => setSel(r.id)} style={{ cursor: "pointer", fontWeight: r.id === sel ? 700 : 400 }}>
                  <td>{r.id.slice(0, 15)}</td>{COLS.map(([k]) => <td key={k}>{show(r.summary[k])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {d && (
        <>
          <h2>Run {d.id.slice(0, 15)}{d.compare_to ? <span style={{ color: "var(--muted)", fontWeight: 400, fontSize: 14 }}> vs the one before</span> : null}</h2>
          {d.compare_to && (
            <div>
              {Object.entries(d.deltas).map(([k, v]) => (
                <span key={k} className={`pill ${v.better ? "pass" : "fail"}`} style={{ marginRight: 6 }}>{k} {v.was} → {v.now}</span>
              ))}
              {Object.keys(d.deltas).length === 0 && <span>No headline metric moved.</span>}
              {d.regressions.length > 0 && <div className="err">Regressions: {d.regressions.join(", ")}. These passed last time.</div>}
              {d.fixed.length > 0 && <div>Fixed: {d.fixed.join(", ")}</div>}
            </div>
          )}

          <h3>Failures ({d.failures.length})</h3>
          {d.failures.length === 0 && <p>None.</p>}
          {d.failures.map((f) => (
            <details key={f.doc} className="card" style={{ marginBottom: 8 }}>
              <summary><strong>{f.doc}</strong>{" "}
                {f.error ? <span className="pill error">error</span> : <>
                  {f.bad?.map((b) => <span key={b.field} className="pill fail" style={{ marginRight: 4 }}>{b.field}</span>)}
                  {f.not_flagged && <span className="pill warn">not flagged</span>}</>}
              </summary>
              {f.error && <pre>{f.error}</pre>}
              {f.bad?.map((b) => <div key={b.field}><code>{b.field}</code>: got <code>{JSON.stringify(b.got)}</code>, want <code>{JSON.stringify(b.want)}</code></div>)}
              {f.not_flagged && <div>Should have gone to a human: {f.why ?? "(no reason in the gold set)"} (confidence {f.confidence})</div>}
              {f.text && <pre style={{ marginTop: 8 }}>{f.text}</pre>}
              <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 6 }}>Write down why before you fix it: wrong prompt, wrong schema, wrong gold, or a document nobody could read?</div>
            </details>
          ))}

          <h3>Review routing</h3>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
            <label>A wrong auto-posted invoice costs GHS <input value={wrong} onChange={(e) => setWrong(e.target.value)} style={{ width: 90 }} inputMode="decimal" /></label>
            <label>A human review costs GHS <input value={review} onChange={(e) => setReview(e.target.value)} style={{ width: 90 }} inputMode="decimal" /></label>
          </div>
          <table>
            <thead><tr><th>Threshold</th><th>Auto</th><th>Wrong on auto</th><th>Error rate</th><th>Must-review leaked</th>{d.routing[0]?.cost_per_doc !== undefined && <th>GHS / doc</th>}</tr></thead>
            <tbody>
              {d.routing.map((r) => {
                const best = d.routing[0]?.cost_per_doc !== undefined ? Math.min(...d.routing.map((x) => x.cost_per_doc ?? Infinity)) : null;
                return (
                  <tr key={r.threshold} style={best !== null && r.cost_per_doc === best ? { fontWeight: 700 } : undefined}>
                    <td>{r.threshold}</td><td>{r.auto} ({Math.round(r.auto_pct * 100)}%)</td><td>{r.wrong_on_auto}</td>
                    <td>{r.error_rate_on_auto === null ? "–" : `${(r.error_rate_on_auto * 100).toFixed(1)}%`}</td><td>{r.leaked}</td>
                    {r.cost_per_doc !== undefined && <td>{r.cost_per_doc}</td>}
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p style={{ color: "var(--muted)", fontSize: 13 }}>
            Fill in both costs and the cheapest row is bold. With a small gold set the table is noisy: a threshold that &quot;wins&quot; on ten
            documents proves little, which is why the plan has you grow it to 30+. A leaked must-review document outweighs any saving.
          </p>
        </>
      )}
    </>
  );
}
