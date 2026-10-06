"use client";

import { useCallback, useEffect, useState } from "react";
import Conditions from "@/components/Conditions";
import { CheckResult, Run, RunSummary, sim } from "@/lib/sim";

type Listing = { title: string; checks: { id: string; section: string; title: string; points: number }[]; runs: RunSummary[] };

export default function LabRunner({ lab, contract }: { lab: string; contract: React.ReactNode }) {
  const [tab, setTab] = useState<"run" | "contract">("run");
  const [listing, setListing] = useState<Listing | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showAllHints, setShowAllHints] = useState(false);

  const refresh = useCallback(async () => {
    const l = await sim<Listing>(`/checks/${lab}/runs`);
    setListing(l);
    return l;
  }, [lab]);

  const open = useCallback(async (runId: string) => setRun(await sim<Run>(`/checks/${lab}/runs/${runId}`)), [lab]);

  useEffect(() => {
    refresh()
      .then((l) => (l.runs.length ? open(l.runs.at(-1)!.run_id) : null))
      .catch((e) => setErr(e.message));
  }, [refresh, open]);

  async function go() {
    setBusy(true);
    setErr(null);
    try {
      setRun(await sim<Run>(`/checks/${lab}/run`, { method: "POST" }));
      await refresh();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const firstFailure = run?.results.find((r) => r.status === "fail" || r.status === "error")?.id;
  const sections = run ? groupBy(run.results) : listing ? groupBy(listing.checks as unknown as CheckResult[]) : [];

  return (
    <>
      <div className="tabs">
        <button className={tab === "run" ? "on" : ""} onClick={() => setTab("run")}>Run &amp; results</button>
        <button className={tab === "contract" ? "on" : ""} onClick={() => setTab("contract")}>Contract</button>
      </div>

      {tab === "contract" && contract}

      {tab === "run" && (
        <>
          <Conditions lab={lab} />
          <div className="card">
            <div className="row">
              <div>
                {run ? (
                  <>
                    <span className="score">{run.score}</span>
                    <span className="muted"> / {run.total} pts · {run.passed}/{run.count} checks</span>
                    <div className="small muted">Run {run.run_id} against {run.learner_url}</div>
                  </>
                ) : (
                  <span className="muted">No runs yet.</span>
                )}
              </div>
              <div className="spacer" />
              <label className="small muted row" style={{ gap: 6 }}>
                <input type="checkbox" checked={showAllHints} onChange={(e) => setShowAllHints(e.target.checked)} />
                show every hint
              </label>
              <button className="btn" onClick={go} disabled={busy}>{busy ? "Running… (~20s)" : "Run checker"}</button>
            </div>
            {listing && listing.runs.length > 1 && (
              <div style={{ marginTop: 14 }}>
                <div className="small muted" style={{ marginBottom: 4 }}>History (click a bar)</div>
                <div className="history">
                  {listing.runs.map((r) => (
                    <button
                      key={r.run_id}
                      title={`${r.run_id}: ${r.score}/${r.total}`}
                      className={run?.run_id === r.run_id ? "active" : ""}
                      style={{ height: `${Math.max(4, (60 * r.score) / r.total)}px` }}
                      onClick={() => open(r.run_id)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
          {err && <div className="err">{err}</div>}

          {sections.map(([section, rows]) => (
            <div key={section}>
              <h2>{section}</h2>
              <div className="card">
                {rows.map((r) => (
                  <div className="result" key={r.id}>
                    <div className="row">
                      {r.status ? <span className={`pill ${r.status}`}>{r.status}</span> : <span className="pill warn">not run</span>}
                      <strong>{r.title}</strong>
                      <div className="spacer" />
                      <span className="small muted">{r.points} pts</span>
                    </div>
                    {r.status && r.status !== "pass" && <div className="detail">{r.detail}</div>}
                    {r.hint && (showAllHints || r.id === firstFailure) && <p className="hint">Hint: {r.hint}</p>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </>
      )}
    </>
  );
}

function groupBy(rows: CheckResult[]): [string, CheckResult[]][] {
  const out = new Map<string, CheckResult[]>();
  for (const r of rows) out.set(r.section, [...(out.get(r.section) ?? []), r]);
  return [...out.entries()];
}
