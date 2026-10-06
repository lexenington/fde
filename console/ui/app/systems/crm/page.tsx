"use client";

import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

const STAGES = ["new", "qualified", "contract_sent", "won", "lost"];

type Deal = { id: string; name: string; amount_ghs: number; stage: string; owner_email: string; contact_id: string; properties: Record<string, string>; notes: { note_id: string; text: string }[] };
type State = {
  contacts: { id: string; email: string; name: string | null; phone: string | null }[];
  deals: Deal[];
  requests: { at: string; method: string; path: string; status: number; retry_after: string | null }[];
  deliveries: { at: string; event_id: string; type: string; status: number | null; error?: string; label: string }[];
  chaos: { force_429: number; retry_after: number };
  settings: { learner_url: string };
};

export default function CrmPage() {
  const [s, setS] = useState<State | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [url, setUrl] = useState("");
  const [n429, setN429] = useState(3);
  const [ra, setRa] = useState(2);
  const [notes, setNotes] = useState<Record<string, string>>({});

  const load = () => sim<State>("/admin/state").then((x) => { setS(x); setErr(null); setUrl((u) => u || x.settings.learner_url); }).catch((e) => setErr(e.message));
  useEffect(() => { load(); const t = setInterval(load, 2000); return () => clearInterval(t); }, []);

  const act = (p: Promise<unknown>) => p.then(load).catch((e) => setErr(e.message));

  return (
    <>
      <h1>CRM</h1>
      <p className="lede">
        Adom&apos;s CRM, as their sales team sees it. Your app calls its API at <code>http://localhost:8090/crm/v3</code>.
        When you change a stage or add a note here, it sends a signed webhook to your app, with retries, as a real CRM would.
      </p>
      {err && <div className="err">{err}</div>}

      <div className="grid">
        <div className="card">
          <h3>Your app&apos;s URL</h3>
          <div className="small muted">Where webhooks and checkers go. From Docker, your machine is <code>host.docker.internal</code>.</div>
          <div className="row" style={{ marginTop: 8 }}>
            <input style={{ flex: 1 }} value={url} onChange={(e) => setUrl(e.target.value)} />
            <button className="btn ghost" onClick={() => act(sim("/admin/settings", { method: "PUT", json: { learner_url: url } }))}>Save</button>
          </div>
        </div>
        <div className="card">
          <h3>Chaos: rate limiting</h3>
          <div className="small muted">
            Next {s?.chaos.force_429 ?? 0} API calls will get 429. Normal limit: 5 req/s, burst 10.
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <input type="number" min={0} style={{ width: 64 }} value={n429} onChange={(e) => setN429(+e.target.value)} /> calls,
            Retry-After <input type="number" min={1} style={{ width: 56 }} value={ra} onChange={(e) => setRa(+e.target.value)} />s
            <button className="btn ghost" onClick={() => act(sim("/admin/chaos", { json: { force_429: n429, retry_after: ra } }))}>Arm</button>
          </div>
        </div>
        <div className="card">
          <h3>Reset</h3>
          <div className="small muted">Wipes contacts, deals and logs. Your app&apos;s own database will still point at old ids.</div>
          <button className="btn ghost" style={{ marginTop: 8 }} onClick={() => confirm("Wipe the CRM?") && act(sim("/admin/reset", { method: "POST" }))}>Wipe CRM</button>
        </div>
      </div>

      <h2>Deals ({s?.deals.length ?? 0})</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Deal</th><th>Owner</th><th>booking_id</th><th>Stage (sends webhook)</th><th>Notes</th></tr></thead>
          <tbody>
            {s?.deals.map((d) => (
              <tr key={d.id}>
                <td><code>{d.id}</code><div className="small">{d.name} · GHS {d.amount_ghs.toLocaleString()}</div></td>
                <td className="small">{d.owner_email}</td>
                <td className="small"><code>{d.properties.booking_id ?? "—"}</code></td>
                <td>
                  <select value={d.stage} onChange={(e) => act(sim(`/admin/deals/${d.id}/stage`, { json: { stage: e.target.value } }))}>
                    {STAGES.map((x) => <option key={x}>{x}</option>)}
                  </select>
                </td>
                <td>
                  <div className="small">{d.notes.length} note(s)</div>
                  <div className="row" style={{ marginTop: 4 }}>
                    <input placeholder="add a note…" value={notes[d.id] ?? ""} onChange={(e) => setNotes({ ...notes, [d.id]: e.target.value })} />
                    <button className="btn ghost" disabled={!notes[d.id]} onClick={() => { act(sim(`/admin/deals/${d.id}/notes`, { json: { text: notes[d.id] } })); setNotes({ ...notes, [d.id]: "" }); }}>Add</button>
                  </div>
                </td>
              </tr>
            ))}
            {s && !s.deals.length && <tr><td colSpan={5} className="muted">No deals yet. Your app creates them.</td></tr>}
          </tbody>
        </table>
      </div>

      <h2>Webhook deliveries</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>At</th><th>Event</th><th>Your app answered</th><th></th></tr></thead>
          <tbody>
            {s?.deliveries.slice(0, 40).map((d, i) => (
              <tr key={i}>
                <td className="small">{d.at.slice(11)}</td>
                <td className="small"><code>{d.event_id}</code> {d.type}<div className="muted">{d.label}</div></td>
                <td>{d.status ? <span className={`pill ${d.status < 300 ? "pass" : "fail"}`}>{d.status}</span> : <span className="pill fail">{d.error ?? "no answer"}</span>}</td>
                <td><button className="btn ghost" onClick={() => act(sim(`/admin/events/${d.event_id}/redeliver`, { method: "POST" }))}>Redeliver</button></td>
              </tr>
            ))}
            {s && !s.deliveries.length && <tr><td colSpan={4} className="muted">Nothing sent yet.</td></tr>}
          </tbody>
        </table>
      </div>

      <h2>API calls from your app</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>At</th><th>Request</th><th>Status</th></tr></thead>
          <tbody>
            {s?.requests.slice(0, 60).map((r, i) => (
              <tr key={i}>
                <td className="small">{r.at}</td>
                <td className="small"><code>{r.method} {r.path}</code></td>
                <td><span className={`pill ${r.status < 300 ? "pass" : r.status === 429 ? "warn" : "fail"}`}>{r.status}{r.retry_after ? ` · Retry-After ${r.retry_after}` : ""}</span></td>
              </tr>
            ))}
            {s && !s.requests.length && <tr><td colSpan={3} className="muted">No calls yet.</td></tr>}
          </tbody>
        </table>
      </div>

      <h2>Contacts ({s?.contacts.length ?? 0})</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Id</th><th>Email</th><th>Name</th><th>Phone</th></tr></thead>
          <tbody>
            {s?.contacts.map((c) => (
              <tr key={c.id}><td><code>{c.id}</code></td><td>{c.email}</td><td>{c.name}</td><td>{c.phone}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
