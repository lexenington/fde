"use client";

import { useCallback, useEffect, useState } from "react";
import Conditions from "@/components/Conditions";
import { CheckResult, Run, RunSummary, sim } from "@/lib/sim";

type Listing = { title: string; async?: boolean; checks: { id: string; section: string; title: string; points: number }[]; runs: RunSummary[] };

export default function LabRunner({ lab, contract }: { lab: string; contract?: React.ReactNode }) {
  const [tab, setTab] = useState<"run" | "contract">("run");
  const [listing, setListing] = useState<Listing | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showAllHints, setShowAllHints] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number; latest: string } | null>(null);
  const [only, setOnly] = useState("");

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
      if (listing?.async) {
        // long suites run in the background; poll until they finish
        await sim(`/checks/${lab}/start${only ? `?only=${encodeURIComponent(only)}` : ""}`, { method: "POST" });
        for (;;) {
          await new Promise((r) => setTimeout(r, 2500));
          const p = await sim<{ state: string; done: number; total: number; latest: string; run_id: string | null; error: string | null }>(`/checks/${lab}/progress`);
          setProgress({ done: p.done, total: p.total, latest: p.latest });
          if (p.state === "error") throw new Error(p.error ?? "the run failed");
          if (p.state === "done" && p.run_id) { await open(p.run_id); break; }
        }
      } else {
        setRun(await sim<Run>(`/checks/${lab}/run`, { method: "POST" }));
      }
      await refresh();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  const firstFailure = run?.results.find((r) => r.status === "fail" || r.status === "error")?.id;
  const sections = run ? groupBy(run.results) : listing ? groupBy(listing.checks as unknown as CheckResult[]) : [];

  return (
    <>
      {contract && (
        <div className="tabs">
          <button className={tab === "run" ? "on" : ""} onClick={() => setTab("run")}>Run &amp; results</button>
          <button className={tab === "contract" ? "on" : ""} onClick={() => setTab("contract")}>Contract</button>
        </div>
      )}

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
              {listing?.async && (
                <select value={only} onChange={(e) => setOnly(e.target.value)} disabled={busy} title="Run only one section">
                  <option value="">All sections</option>
                  {[...new Set(listing.checks.map((c) => c.section))].filter((x) => x !== "Setup").map((x) => <option key={x}>{x}</option>)}
                </select>
              )}
              <button className="btn" onClick={go} disabled={busy}>
                {busy ? (progress ? `Running ${progress.done}/${progress.total}…` : "Starting…") : listing?.async ? "Run acceptance test" : "Run checker"}
              </button>
            </div>
            {busy && progress?.latest && <div className="small muted" style={{ marginTop: 8 }}>Finished: {progress.latest}</div>}
            {run?.summary && <Summary s={run.summary} />}
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

function Card({ big, tag, ok, children }: { big: React.ReactNode; tag?: string; ok?: boolean; children: React.ReactNode }) {
  return (
    <div className="card">
      <div className="row"><span className="score">{big}</span>{tag && <span className={`pill ${ok ? "pass" : "fail"}`}>{tag}</span>}</div>
      <div className="small muted">{children}</div>
    </div>
  );
}

function Summary({ s }: { s: NonNullable<Run["summary"]> }) {
  const safetyOk = s.safety_failures === 0;
  if (s.answer_total !== undefined) {           // Savanna
    const pct = (a?: number, b?: number) => (b ? Math.round((100 * (a ?? 0)) / b) : 0);
    return (
      <div className="grid" style={{ marginTop: 14 }}>
        <Card big={`${pct(s.answer_correct, s.answer_total)}%`}>answer accuracy: {s.answer_correct}/{s.answer_total} policy questions</Card>
        <Card big={`${pct(s.citation_correct, s.answer_total)}%`}>citation accuracy: {s.citation_correct}/{s.answer_total}</Card>
        <Card big={`${s.abstain_correct}/${s.abstain_total}`}>declined or flagged correctly. False abstentions on answerable questions: {s.false_abstentions}</Card>
        <Card big={`${s.member_correct}/${s.member_total}`}>member summaries exactly right</Card>
        <Card big={s.safety_failures} tag={safetyOk ? "meets the bar" : "must be zero"} ok={safetyOk}>isolation and audit failures, out of {s.safety_total}</Card>
      </div>
    );
  }
  const bookingOk = s.booking_pct != null && s.booking_pct >= 90;
  return (
    <div className="grid" style={{ marginTop: 14 }}>
      <Card big={`${s.booking_pct ?? "–"}%`} tag={bookingOk ? "meets the bar" : "below 90%"} ok={bookingOk}>booking slice: {s.booking_passed}/{s.booking_total} conversations</Card>
      <Card big={s.safety_failures} tag={safetyOk ? "meets the bar" : "must be zero"} ok={safetyOk}>safety slice failures, out of {s.safety_total}</Card>
    </div>
  );
}

function groupBy(rows: CheckResult[]): [string, CheckResult[]][] {
  const out = new Map<string, CheckResult[]>();
  for (const r of rows) out.set(r.section, [...(out.get(r.section) ?? []), r]);
  return [...out.entries()];
}
