"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type Char = { id: string; name: string; role: string; org: string; public_brief: string; call_goal: string };
type Scenario = { scenario: string; title: string; lab: string; context: string; characters: Char[] };

export default function Stakeholders() {
  const router = useRouter();
  const [data, setData] = useState<{ llm_ready: boolean; scenarios: Scenario[] } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => { sim("/chat/scenarios").then(setData).catch((e) => setErr(e.message)); }, []);

  async function start(scenario: string, character: string) {
    setBusy(character);
    try {
      const v = await sim<{ session_id: string }>("/chat/calls", { json: { scenario, character } });
      router.push(`/stakeholders/call/${v.session_id}`);
    } catch (e) { setErr((e as Error).message); setBusy(null); }
  }

  return (
    <>
      <h1>Stakeholder calls</h1>
      <p className="lede">
        Claude plays the people in each engagement. They know things you don&apos;t, and they only tell you when you ask
        well. Run the call like a real discovery call: be curious, ask for the last time it happened, find out who else
        decides, and close with a next step. Afterwards you get a scored debrief, and the transcript is saved to
        <code> 03-customer-craft/practice/</code>.
      </p>
      {data && !data.llm_ready && (
        <div className="err">
          Claude isn&apos;t connected. Export <code>ANTHROPIC_API_KEY</code> in the shell where you run
          <code> docker compose up</code> (then <code>docker compose up -d sim</code>) to start calls.
        </div>
      )}
      {err && <div className="err">{err}</div>}

      {data?.scenarios.map((s) => (
        <section key={s.scenario}>
          <h2>{s.title} <span className="muted small">· {s.lab}</span></h2>
          <p className="small muted" style={{ maxWidth: 780 }}>{s.context}</p>
          <div className="grid">
            {s.characters.map((c) => (
              <div className="card" key={c.id}>
                <h3 style={{ marginBottom: 0 }}>{c.name}</h3>
                <div className="small muted" style={{ marginBottom: 8 }}>{c.role}</div>
                <p className="small">{c.public_brief}</p>
                <p className="small muted"><strong>Your goal:</strong> {c.call_goal}</p>
                <button className="btn" disabled={!data.llm_ready || busy !== null} onClick={() => start(s.scenario, c.id)}>
                  {busy === c.id ? "Connecting…" : "Start call"}
                </button>
              </div>
            ))}
          </div>
        </section>
      ))}
    </>
  );
}
