"use client";

import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type Call = { at: string; system: string; method: string; path: string; query: string; status: number; accept: string };
type State = {
  chaos: { snow_429: number; snow_503: number; sap_slow_ms: number; sap_locked: string[]; sap_etag_bump: number; retry_after: number };
  incidents_total: number;
  incidents: { number: string; short_description: string; state: string; priority: string; caller: string; correlation_id: string; created: string }[];
  orders: { SalesOrder: string; customer: string; total: string; processing: string; delivery: string; block: string; locked: boolean }[];
  calls: Call[];
  credentials: { servicenow: { base_url: string; user: string; password: string }; sap: { base_url: string; user: string; password: string; sap_client: string } };
};

export default function Platforms() {
  const [st, setSt] = useState<State | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = () => sim<State>("/platforms/state").then(setSt).catch((e) => setErr(e.message));
  useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t); }, []);
  const chaos = (body: object) => sim<State>("/platforms/chaos", { json: body }).then(setSt).catch((e) => setErr(e.message));
  const reset = () => sim<State>("/platforms/reset", { method: "POST" }).then(setSt).catch((e) => setErr(e.message));

  return (
    <>
      <h1>Volta: ServiceNow &amp; SAP</h1>
      <p className="lede">
        What Volta&apos;s two systems hold right now, every call your app is making to them, and switches for the bad days. The 02/06 checker
        flips these itself; use them by hand to see how your tool layer behaves. <strong>Reset</strong> restores the seed data and clears everything.
      </p>
      {err && <div className="err">{err}</div>}

      {st && (
        <>
          <div className="card" style={{ display: "grid", gap: 6, gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
            <div>
              <strong>ServiceNow</strong> (Table API, Basic auth)<br />
              <code style={{ overflowWrap: "anywhere" }}>{st.credentials.servicenow.base_url}/api/now/table/incident</code><br />
              user <code>{st.credentials.servicenow.user}</code> · password <code>{st.credentials.servicenow.password}</code>
            </div>
            <div>
              <strong>SAP</strong> (OData v2, Basic auth)<br />
              <code style={{ overflowWrap: "anywhere" }}>{st.credentials.sap.base_url}</code><br />
              user <code>{st.credentials.sap.user}</code> · password <code>{st.credentials.sap.password}</code> · client <code>{st.credentials.sap.sap_client}</code>
            </div>
          </div>

          <h2>Bad days</h2>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button onClick={() => chaos({ snow_429: 3 })}>ServiceNow: next 3 calls 429 {st.chaos.snow_429 > 0 && `(${st.chaos.snow_429} left)`}</button>
            <button onClick={() => chaos({ snow_503: 3 })}>ServiceNow: hibernating for 3 calls {st.chaos.snow_503 > 0 && `(${st.chaos.snow_503} left)`}</button>
            <button onClick={() => chaos({ sap_slow_ms: st.chaos.sap_slow_ms ? 0 : 3000 })}>SAP slow (3 s): {st.chaos.sap_slow_ms ? "ON" : "off"}</button>
            <button onClick={() => chaos({ sap_locked: st.chaos.sap_locked.length ? [] : ["0000012350"] })}>Lock order 0000012350: {st.chaos.sap_locked.length ? "ON" : "off"}</button>
            <button onClick={() => chaos({ sap_etag_bump: 1 })}>SAP: next write finds the order changed {st.chaos.sap_etag_bump > 0 && "(armed)"}</button>
            <button onClick={reset}>Reset everything</button>
          </div>

          <h2>ServiceNow incidents <span style={{ color: "var(--muted)", fontSize: 14, fontWeight: 400 }}>({st.incidents_total} total, newest 25)</span></h2>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead><tr><th>Number</th><th>Summary</th><th>State</th><th>P</th><th>Caller</th><th>correlation_id</th></tr></thead>
              <tbody>{st.incidents.map((i) => (
                <tr key={i.number}><td><code>{i.number}</code></td><td>{i.short_description}</td><td>{i.state}</td><td>{i.priority}</td><td>{i.caller}</td><td><code>{i.correlation_id || "–"}</code></td></tr>))}</tbody>
            </table>
          </div>

          <h2>SAP sales orders</h2>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead><tr><th>Order</th><th>Customer</th><th>Net (GHS)</th><th>Processing</th><th>Delivery</th><th>Block</th></tr></thead>
              <tbody>{st.orders.map((o) => (
                <tr key={o.SalesOrder}><td><code>{o.SalesOrder}</code> {o.locked && <span className="pill warn">locked</span>}</td><td>{o.customer}</td><td>{o.total}</td>
                  <td>{o.processing}</td><td>{o.delivery}</td><td>{o.block ? <span className="pill fail">{o.block}</span> : "–"}</td></tr>))}</tbody>
            </table>
          </div>

          <h2>Calls from your app</h2>
          {st.calls.length === 0 ? <p>None yet. Call one of the two APIs and it shows up here.</p> : (
            <div style={{ overflowX: "auto" }}>
              <table>
                <thead><tr><th>At</th><th></th><th>Request</th><th>Status</th></tr></thead>
                <tbody>{st.calls.map((c, i) => (
                  <tr key={i}><td>{c.at}</td><td>{c.system}</td><td><code style={{ overflowWrap: "anywhere" }}>{c.method} {c.path}{c.query ? `?${c.query.slice(0, 90)}` : ""}</code></td>
                    <td><span className={`pill ${c.status < 300 ? "pass" : c.status < 500 ? "warn" : "fail"}`}>{c.status}</span></td></tr>))}</tbody>
              </table>
            </div>
          )}
        </>
      )}
    </>
  );
}
