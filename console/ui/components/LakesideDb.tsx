"use client";

import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type Info = {
  database: { host: string; port: number; dbname: string; read_user: string; read_password: string; write_user: string; write_password: string;
    stats: { clinics?: number; patients?: number; slots?: number; appointments?: number; backup_window?: boolean; error?: string }; notes: string };
  bsp: { base_url: string; token: string; webhook_secret: string; stt_url: string; templates: Record<string, { text: string; params: number }> };
  learner_url: string; dup_inbound: boolean;
};

export default function LakesideDb() {
  const [i, setI] = useState<Info | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = () => sim<Info>("/lakeside/info").then(setI).catch((e) => setErr(e.message));
  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, []);
  const act = async (p: Promise<unknown>) => { setBusy(true); setErr(null); try { await p; await load(); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); } };
  if (!i) return err ? <div className="err">{err}</div> : <p className="muted">Loading…</p>;
  const d = i.database, s = d.stats;

  return (
    <>
      {err && <div className="err">{err}</div>}
      <h3>What IT gave you</h3>
      <div className="table-wrap">
        <table><tbody>
          <tr><th>Database (read replica)</th><td><code>postgresql://{d.read_user}:{d.read_password}@{d.host}:{d.port}/{d.dbname}</code></td></tr>
          <tr><th>Write path</th><td><code>postgresql://{d.write_user}:{d.write_password}@{d.host}:{d.port}/{d.dbname}</code> can only run <code>create_booking(phone, clinic, slot)</code> and <code>cancel_booking(appt)</code></td></tr>
          <tr><th>WhatsApp provider</th><td><code>{i.bsp.base_url}</code> with <code>Authorization: Bearer {i.bsp.token}</code></td></tr>
          <tr><th>Webhook signing secret</th><td><code>{i.bsp.webhook_secret}</code>, header <code>X-BSP-Signature</code></td></tr>
          <tr><th>Speech-to-text</th><td><code>POST {i.bsp.stt_url}</code></td></tr>
          <tr><th>Approved templates</th><td className="small">{Object.entries(i.bsp.templates).map(([k, v]) => <div key={k}><code>{k}</code> ({v.params} params): {v.text}</div>)}</td></tr>
        </tbody></table>
      </div>
      <p className="small muted">{d.notes}</p>

      <h3>The database right now</h3>
      {s.error ? <div className="err">{s.error}</div> : (
        <div className="grid">
          {(["clinics", "patients", "slots", "appointments"] as const).map((k) => <div className="card" key={k}><div className="score">{(s[k] ?? 0).toLocaleString()}</div><div className="small muted">{k}</div></div>)}
        </div>
      )}
      <p className="small muted">Dates are relative to today, so slots are always in the future. Try a read: <code>psql &quot;postgresql://{d.read_user}:{d.read_password}@localhost:{d.port}/{d.dbname}&quot;</code></p>

      <h3>Make the customer misbehave</h3>
      <div className="grid">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Nightly backup window</h3>
          <p className="small muted">Between 1am and 2am the slots table locks and every write times out. Turn it on and see whether your bot admits it, or claims a booking it didn&apos;t make.</p>
          <button className={`btn ${s.backup_window ? "" : "ghost"}`} disabled={busy} onClick={() => act(sim("/lakeside/db/backup-window", { json: { on: !s.backup_window } }))}>
            {s.backup_window ? "Backup window is ON (click to end)" : "Start the backup window"}
          </button>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Duplicate deliveries</h3>
          <p className="small muted">Providers deliver at least once. When this is on, every inbound message is delivered twice.</p>
          <button className={`btn ${i.dup_inbound ? "" : "ghost"}`} disabled={busy} onClick={() => act(sim("/lakeside/chaos/duplicates", { json: { on: !i.dup_inbound } }))}>
            {i.dup_inbound ? "Duplicates are ON (click to stop)" : "Deliver everything twice"}
          </button>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Start over</h3>
          <p className="small muted">Rebuild the database from scratch (new random patients and slots) and clear all WhatsApp conversations.</p>
          <button className="btn ghost" disabled={busy} onClick={() => confirm("Rebuild the whole database?") && act(Promise.all([sim("/lakeside/db/reset", { method: "POST" }), sim("/lakeside/conversations/reset", { method: "POST" })]))}>
            {busy ? "Working…" : "Rebuild the database"}
          </button>
        </div>
      </div>
    </>
  );
}
