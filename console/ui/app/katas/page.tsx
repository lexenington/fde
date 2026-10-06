"use client";

import { useEffect, useState } from "react";
import Markdown from "@/components/Markdown";
import { sim } from "@/lib/sim";

type Kata = { id: string; title: string; timebox: string; used_in: string };
type Result = { passed: number; failed: number; output: string; timed_out: boolean };

export default function Katas() {
  const [katas, setKatas] = useState<Kata[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [readme, setReadme] = useState<string>("");
  const [results, setResults] = useState<Record<string, Result>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { sim<{ katas: Kata[] }>("/katas").then((d) => setKatas(d.katas)).catch((e) => setErr(e.message)); }, []);

  async function show(id: string) {
    setOpen(id);
    setReadme("");
    try { setReadme((await sim<{ readme: string }>(`/katas/${id}`)).readme); } catch (e) { setErr((e as Error).message); }
  }

  async function run(id: string) {
    setBusy(id); setErr(null);
    try { const r = await sim<Result>(`/katas/${id}/run`, { method: "POST" }); setResults((x) => ({ ...x, [id]: r })); }
    catch (e) { setErr((e as Error).message); }
    setBusy(null);
  }

  const done = Object.values(results).filter((r) => r.failed === 0 && r.passed > 0).length;

  return (
    <>
      <h1>Katas</h1>
      <p className="lede">
        Thirty to sixty minutes each, tests already written and red. Open the folder in <code>katas/</code>, make the tests
        pass, then run them here. One kata on Monday is the warm-up for the week&apos;s lab; the README says which.
        {katas && <> <strong>{done}/{katas.length}</strong> green in this session.</>}
      </p>
      {err && <div className="err">{err}</div>}
      {katas && katas.length === 0 && <div className="err">No katas found. Is <code>../katas</code> mounted into the sim container?</div>}
      <div style={{ display: "grid", gap: 10 }}>
        {katas?.map((k) => {
          const r = results[k.id];
          return (
            <div key={k.id} className="card">
              <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <strong style={{ flex: 1, minWidth: 200 }}>{k.title}</strong>
                {k.timebox && <span className="pill warn">{k.timebox}</span>}
                {r && <span className={`pill ${r.failed === 0 && r.passed > 0 ? "pass" : "fail"}`}>{r.passed} pass / {r.failed} fail</span>}
                <button onClick={() => (open === k.id ? setOpen(null) : show(k.id))}>{open === k.id ? "Hide" : "Brief"}</button>
                <button onClick={() => run(k.id)} disabled={busy === k.id}>{busy === k.id ? "Running…" : "Run tests"}</button>
              </div>
              {k.used_in && <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>Used in: {k.used_in}</div>}
              {open === k.id && <div style={{ marginTop: 10 }}><Markdown source={readme} /></div>}
              {r && r.failed + (r.timed_out ? 1 : 0) > 0 && <pre style={{ marginTop: 10 }}>{r.output}</pre>}
            </div>
          );
        })}
      </div>
    </>
  );
}
