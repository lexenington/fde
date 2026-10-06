"use client";

import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type Mark = { at: number; minutes: number; note: string };
type Ramp = { n: number; codebase: string; started: number; ended: number | null; abandoned?: boolean; marks: Record<string, Mark>; elapsed_min: number; over_day: boolean };
type Doc = { doc: string; exists: boolean; words?: number; checks: { label: string; ok: boolean }[] };
type State = {
  day_hours: number; milestones: { key: string; label: string }[]; active: number | null; ramps: Ramp[]; docs: Doc[]; skeleton: string | null;
  compare: { first: number; latest: number; rows: { milestone: string; first: number | null; latest: number | null }[] } | null; lab_path: string;
};

const hm = (min: number) => `${Math.floor(min / 60)}h ${String(Math.round(min % 60)).padStart(2, "0")}m`;

export default function Ramp() {
  const [st, setSt] = useState<State | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [now, setNow] = useState(Date.now() / 1000);
  const apply = (p: Promise<State>) => p.then((s) => { setSt(s); setErr(null); }).catch((e) => setErr(e.message));
  useEffect(() => { apply(sim<State>("/labs/ramp")); }, []);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, []);

  const active = st?.ramps.find((r) => r.n === st.active);
  const elapsed = active ? Math.max(0, (now - active.started) / 60) : 0;
  const dayMin = (st?.day_hours ?? 8) * 60;

  return (
    <>
      <h1>02/05 Unfamiliar territory</h1>
      <p className="lede">
        One timeboxed day on a codebase you have never seen. Start the clock, tick each milestone the moment you reach it, and write one line about
        what happened. At the end you have the real timeline for <code>RAMP-LOG.md</code>, not one reconstructed from memory, and ramp #2 sits beside ramp #1.
      </p>
      {err && <div className="err">{err}</div>}

      {st && !active && (
        <div className="card" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="Codebase (Odoo, ERPNext, Saleor…)" style={{ flex: 1, minWidth: 220 }} />
          <button onClick={() => apply(sim<State>("/labs/ramp/start", { json: { codebase: code } }))}>Start the {st.day_hours}-hour day</button>
        </div>
      )}

      {st && active && (
        <>
          <div className="card" style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
            <strong style={{ fontSize: 28, fontVariantNumeric: "tabular-nums", color: elapsed > dayMin ? "var(--fail)" : undefined }}>{hm(elapsed)}</strong>
            <span>of {st.day_hours}h on <strong>{active.codebase}</strong> (ramp #{active.n})</span>
            <span style={{ flex: 1 }} />
            <button onClick={() => apply(sim<State>("/labs/ramp/finish", { json: {} }))}>End the day</button>
            <button onClick={() => confirm("Abandon this ramp? It won't count in the comparison.") && apply(sim<State>("/labs/ramp/finish?abandon=true", { json: {} }))}>Abandon</button>
          </div>
          <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
            {st.milestones.map((m) => {
              const mk = active.marks[m.key];
              return (
                <div key={m.key} className="card" style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                  <span className={`pill ${mk ? "pass" : "warn"}`}>{mk ? `${hm(mk.minutes)}` : "open"}</span>
                  <strong style={{ flex: 1, minWidth: 220 }}>{m.label}</strong>
                  {mk ? (
                    <>
                      <span style={{ color: "var(--muted)" }}>{mk.note || "no note"}</span>
                      <button onClick={() => apply(sim<State>(`/labs/ramp/unmark/${m.key}`, { json: {} }))}>Undo</button>
                    </>
                  ) : (
                    <>
                      <input value={notes[m.key] ?? ""} onChange={(e) => setNotes({ ...notes, [m.key]: e.target.value })} placeholder="One line: what happened, what cost time" style={{ flex: 2, minWidth: 220 }} />
                      <button onClick={() => apply(sim<State>(`/labs/ramp/mark/${m.key}`, { json: { note: notes[m.key] ?? "" } }))}>Reached it</button>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}

      {st?.skeleton && (
        <>
          <h2>RAMP-LOG.md skeleton</h2>
          <p>Built from your stamps. Paste it into <code>{st.lab_path}/RAMP-LOG.md</code> and add the two sections that matter.</p>
          <pre>{st.skeleton}</pre>
        </>
      )}

      {st && st.ramps.length > 0 && (
        <>
          <h2>Your ramps</h2>
          <table>
            <thead><tr><th>#</th><th>Codebase</th><th>Time</th><th>Milestones</th><th></th></tr></thead>
            <tbody>{st.ramps.map((r) => (
              <tr key={r.n}><td>{r.n}</td><td>{r.codebase}</td><td>{hm(r.elapsed_min)}</td><td>{Object.keys(r.marks).length}/{st.milestones.length}</td>
                <td>{r.ended === null ? <span className="pill warn">running</span> : r.abandoned ? <span className="pill fail">abandoned</span> : <span className={`pill ${r.over_day ? "fail" : "pass"}`}>{r.over_day ? "over the day" : "in the box"}</span>}</td></tr>))}</tbody>
          </table>
        </>
      )}

      {st?.compare && (
        <>
          <h2>Ramp #{st.compare.first} vs ramp #{st.compare.latest}</h2>
          <table>
            <thead><tr><th>Milestone (minutes in)</th><th>#{st.compare.first}</th><th>#{st.compare.latest}</th></tr></thead>
            <tbody>{st.compare.rows.map((r) => (
              <tr key={r.milestone}><td>{r.milestone}</td><td>{r.first ?? "–"}</td>
                <td>{r.latest ?? "–"} {r.first != null && r.latest != null && <span className={`pill ${r.latest <= r.first ? "pass" : "fail"}`}>{r.latest <= r.first ? "faster" : "slower"}</span>}</td></tr>))}</tbody>
          </table>
          <p style={{ color: "var(--muted)", fontSize: 13 }}>The second ramp should be noticeably faster. If a milestone isn&apos;t, that is the thing to practise.</p>
        </>
      )}

      <h2>What you wrote</h2>
      {st?.docs.map((d) => (
        <div key={d.doc} className="card" style={{ marginBottom: 8 }}>
          <strong>{d.doc}</strong> {d.exists ? (d.words ? <span style={{ color: "var(--muted)" }}>{d.words} words</span> : null) : <span className="pill fail">missing</span>}
          <div>{d.checks.map((c) => <span key={c.label} className={`pill ${c.ok ? "pass" : "warn"}`} style={{ marginRight: 6, display: "inline-block", marginTop: 6 }}>{c.ok ? "✓" : "–"} {c.label}</span>)}</div>
        </div>
      ))}
      <p style={{ color: "var(--muted)", fontSize: 13 }}>Looked for in <code>{st?.lab_path}</code>. These are shape checks. The test of a good ARCHITECTURE.md is whether someone else can find where to make a change from it.</p>
    </>
  );
}
