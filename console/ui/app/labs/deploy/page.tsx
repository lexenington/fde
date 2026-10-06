"use client";

import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type Finding = { address: string; rule: string; why: string; fix: string };
type Present = { id: string; label: string; ok: boolean };
type Plan = { ready: boolean; how?: string; resources?: number; findings?: Finding[]; present?: Present[] };
type Drill = { running: { started: number } | null; drills: { finished_at: string; minutes: number; within_bar: boolean; note: string }[]; bar_minutes: number };
type Doc = { doc: string; exists: boolean; words?: number; sections: { label: string; ok: boolean }[] };
type State = { plan: Plan; drill: Drill; docs: Doc[]; lab_path: string };

export default function Deploy() {
  const [st, setSt] = useState<State | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [now, setNow] = useState(Date.now() / 1000);
  const load = () => sim<State>("/labs/deploy").then(setSt).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, []);

  const act = (path: string, json?: unknown) => sim(`/labs/deploy/drill/${path}`, { json: json ?? {} }).then(load).catch((e) => setErr(e.message));
  const run = st?.drill.running;
  const el = run ? Math.max(0, now - run.started) : 0;
  const mm = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  const bar = (st?.drill.bar_minutes ?? 30) * 60;

  return (
    <>
      <h1>02/04 Deploy anywhere</h1>
      <p className="lede">
        Nothing here talks to AWS. It reads what you produce in <code>{st?.lab_path ?? "02-technical-depth/04-deploy-anywhere/lab"}</code> and
        reviews it the way Adom&apos;s platform team would: the plan, the teardown drill, and the two documents. Re-run
        <code> terraform show -json</code> and reload to re-review.
      </p>
      {err && <div className="err">{err}</div>}

      <h2>1. Your plan, reviewed</h2>
      {st && !st.plan.ready && <div className="err">{st.plan.how}</div>}
      {st?.plan.ready && (
        <>
          <p>{st.plan.resources} resources would be created or changed. Components the brief requires:</p>
          <p>{st.plan.present?.map((p) => <span key={p.id} className={`pill ${p.ok ? "pass" : "fail"}`} style={{ marginRight: 6, display: "inline-block", marginBottom: 6 }}>{p.ok ? "✓" : "✗"} {p.label}</span>)}</p>
          {st.plan.findings?.length === 0 ? <p><span className="pill pass">No exposure findings.</span> Read the plan yourself anyway: this checks a short list.</p> : (
            <table>
              <thead><tr><th>Resource</th><th>Rule</th><th>Why they will push back</th><th>Fix</th></tr></thead>
              <tbody>{st.plan.findings?.map((f, i) => <tr key={i}><td><code>{f.address}</code></td><td>{f.rule}</td><td>{f.why}</td><td>{f.fix}</td></tr>)}</tbody>
            </table>
          )}
        </>
      )}

      <h2>2. Teardown and rebuild in {st?.drill.bar_minutes ?? 30} minutes</h2>
      <p>Start the timer, run <code>terraform destroy</code>, then <code>terraform apply</code> from zero, and stop it when the service is answering again. Destroy at the end of every session regardless: NAT gateways and ALBs bill while idle.</p>
      <div className="card" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        {run ? (
          <>
            <strong style={{ fontSize: 28, fontVariantNumeric: "tabular-nums", color: el > bar ? "var(--fail)" : undefined }}>{mm(el)}</strong>
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="What slowed you down?" style={{ flex: 1, minWidth: 200 }} />
            <button onClick={() => { act("stop", { note }); setNote(""); }}>Stop: it&apos;s answering</button>
            <button onClick={() => act("cancel")}>Discard</button>
          </>
        ) : <button onClick={() => act("start")}>Start the drill</button>}
      </div>
      {st && st.drill.drills.length > 0 && (
        <table>
          <thead><tr><th>When</th><th>Minutes</th><th>Bar</th><th>Note</th></tr></thead>
          <tbody>{[...st.drill.drills].reverse().map((d, i) => (
            <tr key={i}><td>{d.finished_at.replace("T", " ").replace("+00:00", "")}</td><td>{d.minutes}</td>
              <td><span className={`pill ${d.within_bar ? "pass" : "fail"}`}>{d.within_bar ? "within" : "over"}</span></td><td>{d.note || "–"}</td></tr>))}</tbody>
        </table>
      )}

      <h2>3. Runbook and handover</h2>
      {st?.docs.map((d) => (
        <div key={d.doc} className="card" style={{ marginBottom: 8 }}>
          <strong>{d.doc}</strong> {d.exists ? <span style={{ color: "var(--muted)" }}>{d.words} words</span> : <span className="pill fail">missing</span>}
          <div>{d.sections.map((s) => <span key={s.label} className={`pill ${s.ok ? "pass" : "warn"}`} style={{ marginRight: 6, display: "inline-block", marginTop: 6 }}>{s.ok ? "✓" : "–"} {s.label}</span>)}</div>
        </div>
      ))}
      <p style={{ color: "var(--muted)", fontSize: 13 }}>A heading for each topic is the minimum, not the standard. The test is whether their on-call engineer can follow it at 3am: ask a friend to try, and fix wherever they stall.</p>
    </>
  );
}
