"use client";

import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type Users = { password: string; issuer: string; users: { key: string; email: string; name: string; group: string; note?: string }[] };
type Info = { crm_base_url: string; crm_api_key: string; webhook_secret: string; scim_token: string; issuer: string; audience: string; learner_url: string };
type Tok = { token: string; header: Record<string, unknown>; payload: Record<string, unknown> };

export default function IdentityPage() {
  const [u, setU] = useState<Users | null>(null);
  const [info, setInfo] = useState<Info | null>(null);
  const [tok, setTok] = useState<Tok | null>(null);
  const [who, setWho] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    sim<Users>("/admin/users").then(setU).catch((e) => setErr(e.message));
    sim<Info>("/admin/info").then(setInfo).catch(() => {});
  }, []);

  async function get(user: string, client = "runmysales") {
    setErr(null);
    setWho(`${user} → ${client}`);
    try { setTok(await sim<Tok>(`/admin/token/${user}?client=${client}`)); } catch (e) { setTok(null); setErr((e as Error).message); }
  }

  return (
    <>
      <h1>Identity</h1>
      <p className="lede">
        Adom&apos;s IdP is Keycloak, standing in for Okta or Entra ID. Their IT team created your app as client
        <code> runmysales</code>. SCIM provisioning is pushed by the IdP to your app; in this lab the checker plays that part.
      </p>
      {err && <div className="err">{err}</div>}

      <h2>Connection details (what IT sent you)</h2>
      {info && (
        <div className="table-wrap">
          <table>
            <tbody>
              <tr><th>Issuer</th><td><code>{info.issuer}</code></td></tr>
              <tr><th>Discovery</th><td><code>{info.issuer}/.well-known/openid-configuration</code></td></tr>
              <tr><th>JWKS</th><td><code>{info.issuer}/protocol/openid-connect/certs</code></td></tr>
              <tr><th>Audience</th><td><code>{info.audience}</code></td></tr>
              <tr><th>SCIM bearer token</th><td><code>{info.scim_token}</code> (the IdP sends it to your <code>/scim/v2</code>)</td></tr>
              <tr><th>CRM API</th><td><code>{info.crm_base_url}</code> with <code>Authorization: Bearer {info.crm_api_key}</code></td></tr>
              <tr><th>Webhook secret</th><td><code>{info.webhook_secret}</code></td></tr>
              <tr><th>Keycloak admin</th><td><a href="http://localhost:8081/admin" target="_blank">localhost:8081/admin</a> (admin / admin)</td></tr>
            </tbody>
          </table>
        </div>
      )}

      <h2>People</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>User</th><th>IdP group</th><th>Get a token</th></tr></thead>
          <tbody>
            {u?.users.map((x) => (
              <tr key={x.key}>
                <td>{x.name}<div className="small muted">{x.email}{x.note ? `: ${x.note}` : ""}</div></td>
                <td><code>{x.group}</code></td>
                <td>
                  <div className="row">
                    <button className="btn ghost" onClick={() => get(x.key)}>for runmysales</button>
                    <button className="btn ghost" onClick={() => get(x.key, "other-app")}>for other-app</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {u && <p className="small muted">Every password is <code>{u.password}</code>. Use them for the browser login flow in your app.</p>}

      {tok && (
        <>
          <h2>Token: {who}</h2>
          <p className="small muted">Decoded without verifying, which is exactly what your app must never do. Copy it to try your API with curl.</p>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{tok.token}</pre>
          <div className="grid">
            <div><h3>Header</h3><pre>{JSON.stringify(tok.header, null, 2)}</pre></div>
            <div><h3>Payload</h3><pre>{JSON.stringify(tok.payload, null, 2)}</pre></div>
          </div>
        </>
      )}
    </>
  );
}
