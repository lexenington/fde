"use client";

import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type File = { path: string; title: string; kind: string; pages: number | null };
type Info = {
  as_of: string; files: File[]; sftp: { host: string; port: number; user: string; password: string; path: string };
  issuer: string; audience: string; password: string; learner_url: string;
  users: { key: string; email: string; name: string; role: string; branch: string | null }[];
  branches: Record<string, { name: string; region: string }>;
};
type Tried = { status: number; seconds: number; body: unknown };

const KINDS: Record<string, string> = { policy: "Credit policy", circular: "Circulars (amend the policy)", whatsapp: "WhatsApp export", "field-sheet": "Officers' field sheets" };

export default function SavannaDocs() {
  const [i, setI] = useState<Info | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [user, setUser] = useState("ruth");
  const [mode, setMode] = useState<"ask" | "summary">("ask");
  const [text, setText] = useState("What is the maximum amount a first-time borrower can get on an individual loan?");
  const [asOf, setAsOf] = useState("");
  const [out, setOut] = useState<Tried | null>(null);
  const [busy, setBusy] = useState(false);
  const [tok, setTok] = useState<{ token: string; payload: Record<string, unknown> } | null>(null);

  useEffect(() => {
    const load = () => sim<Info>("/savanna/info").then(setI).catch((e) => setErr(e.message));
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, []);

  async function run() {
    setBusy(true); setErr(null); setOut(null);
    try {
      setOut(mode === "ask"
        ? await sim<Tried>("/savanna/try/ask", { json: { user, question: text, as_of: asOf || null } })
        : await sim<Tried>(`/savanna/try/summary?user=${user}&q=${encodeURIComponent(text)}`));
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  if (!i) return err ? <div className="err">{err}</div> : <p className="muted">Loading…</p>;
  const groups = Object.keys(KINDS).map((k) => [k, i.files.filter((f) => f.kind === k)] as const).filter(([, f]) => f.length);

  return (
    <>
      {err && <div className="err">{err}</div>}
      {!i.files.length && <div className="banner">The documents are still being generated (about 30 seconds on the first start). This page refreshes by itself.</div>}

      <h3>What IT and Risk gave you</h3>
      <div className="table-wrap"><table><tbody>
        <tr><th>Document share</th><td>Download below, or <code>http://localhost:8090/savanna/share/&lt;path&gt;</code></td></tr>
        <tr><th>Core banking drop (SFTP)</th><td><code>sftp://{i.sftp.user}:{i.sftp.password}@{i.sftp.host}:{i.sftp.port}{i.sftp.path}</code>, read-only. Nightly <code>members_</code>, <code>loans_</code> and <code>repayments_</code> CSVs</td></tr>
        <tr><th>Login (Entra stand-in)</th><td>Issuer <code>{i.issuer}</code>, audience <code>{i.audience}</code>. Groups: <code>officers</code> or <code>risk</code>, plus <code>branch-…</code></td></tr>
        <tr><th>Policy &quot;today&quot;</th><td><code>{i.as_of}</code>. Send it as <code>as_of</code>; circulars apply from their effective date.</td></tr>
      </tbody></table></div>

      {groups.map(([kind, files]) => (
        <div key={kind}>
          <h3>{KINDS[kind]}</h3>
          <div className="table-wrap"><table>
            <tbody>
              {files.map((f) => (
                <tr key={f.path}>
                  <td><a href={`/api/sim/savanna/share/${f.path}`} target="_blank">{f.title}</a></td>
                  <td className="small muted">{f.pages ? `${f.pages} page${f.pages === 1 ? "" : "s"}` : f.path.split(".").pop()}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      ))}

      <h3>Officers</h3>
      <div className="table-wrap"><table>
        <thead><tr><th>Officer</th><th>Role</th><th>Branch</th><th></th></tr></thead>
        <tbody>
          {i.users.map((u) => (
            <tr key={u.key}>
              <td>{u.name}<div className="small muted">{u.email}</div></td>
              <td>{u.role}</td><td>{u.branch ? i.branches[u.branch]?.name : "all branches"}</td>
              <td><button className="btn ghost" onClick={() => sim<typeof tok>(`/savanna/token/${u.key}`).then(setTok).catch((e) => setErr(e.message))}>Get a token</button></td>
            </tr>
          ))}
        </tbody>
      </table></div>
      <p className="small muted">Every password is <code>{i.password}</code>.</p>
      {tok && <><pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{tok.token}</pre><pre>{JSON.stringify(tok.payload, null, 2)}</pre></>}

      <h3>Try your copilot as an officer</h3>
      <p className="small muted">Calls your app at <code>{i.learner_url}</code> with a real token for the officer you choose.</p>
      <div className="row" style={{ marginBottom: 8 }}>
        <select value={user} onChange={(e) => setUser(e.target.value)}>{i.users.map((u) => <option key={u.key} value={u.key}>{u.name}</option>)}</select>
        <select value={mode} onChange={(e) => setMode(e.target.value as "ask" | "summary")}>
          <option value="ask">POST /api/ask</option><option value="summary">GET /api/members/summary</option>
        </select>
        {mode === "ask" && <input placeholder={`as_of (default ${i.as_of})`} value={asOf} onChange={(e) => setAsOf(e.target.value)} style={{ width: 170 }} />}
      </div>
      <div className="row">
        <input style={{ flex: 1, minWidth: 260 }} value={text} onChange={(e) => setText(e.target.value)} placeholder={mode === "ask" ? "A question for the copilot" : "Member id, phone number, or name and village"} />
        <button className="btn" disabled={busy || !text.trim()} onClick={run}>{busy ? "Waiting…" : "Send"}</button>
      </div>
      {out && (
        <>
          <p><span className={`pill ${out.status < 300 ? "pass" : "fail"}`}>HTTP {out.status}</span> <span className="small muted">{out.seconds}s</span></p>
          <pre style={{ whiteSpace: "pre-wrap" }}>{typeof out.body === "string" ? out.body : JSON.stringify(out.body, null, 2)}</pre>
        </>
      )}
    </>
  );
}
