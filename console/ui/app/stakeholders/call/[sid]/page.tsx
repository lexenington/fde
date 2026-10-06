"use client";

import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { sim } from "@/lib/sim";

type Msg = { who: "fde" | "them"; text: string };
type Char = { name: string; role: string; org: string; public_brief: string; call_goal: string };
type View = { session_id: string; character: Char; messages: Msg[]; fde_messages: number; max_messages: number };
type Dim = { name: string; score: number; evidence: string; advice: string };
type Fact = { id: string; fact: string; importance: number; question?: string };
type Debrief = {
  character: Char; scenario: string; duration_min: number; talk_ratio: number; discovery_pct: number; average: number;
  dimensions: Dim[]; verdict: string; next_time: string[]; discovered: Fact[]; missed: Fact[]; saved_as: string; transcript: Msg[];
};

const pct = (msgs: Msg[]) => {
  const w = (who: string) => msgs.filter((m) => m.who === who).reduce((n, m) => n + m.text.split(/\s+/).filter(Boolean).length, 0);
  const a = w("fde"), b = w("them");
  return a + b ? Math.round((100 * a) / (a + b)) : 0;
};

export default function Call() {
  const { sid } = useParams<{ sid: string }>();
  const [v, setV] = useState<View | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState<"say" | "end" | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [debrief, setDebrief] = useState<Debrief | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { sim<View>(`/chat/calls/${sid}`).then(setV).catch((e) => setErr(e.message)); }, [sid]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [v?.messages.length, busy]);

  async function send() {
    const t = text.trim();
    if (!t || busy) return;
    setBusy("say"); setErr(null);
    setV((cur) => cur && { ...cur, messages: [...cur.messages, { who: "fde", text: t }] });   // show it right away
    setText("");
    try { setV(await sim<View>(`/chat/calls/${sid}/say`, { json: { text: t } })); }
    catch (e) {
      setErr((e as Error).message);
      setText(t);
      setV((cur) => cur && { ...cur, messages: cur.messages.slice(0, -1) });
    } finally { setBusy(null); }
  }

  async function finish() {
    if (!confirm("End the call and get your debrief?")) return;
    setBusy("end"); setErr(null);
    try { setDebrief(await sim<Debrief>(`/chat/calls/${sid}/end`, { method: "POST" })); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(null); }
  }

  if (debrief) return <DebriefView d={debrief} />;
  if (!v) return err ? <div className="err">{err}</div> : <p className="muted">Connecting…</p>;
  const ratio = pct(v.messages);

  return (
    <>
      <h1>{v.character.name}</h1>
      <p className="lede">{v.character.role} · {v.character.org}</p>
      {err && <div className="err">{err}</div>}
      <div className="call">
        <div className="chat">
          <div className="msgs">
            {v.messages.map((m, i) => (
              <div key={i} className={`bubble ${m.who}`}>
                <div className="who">{m.who === "fde" ? "You" : v.character.name}</div>
                {m.text}
              </div>
            ))}
            {busy === "say" && <div className="bubble them muted">…</div>}
            <div ref={end} />
          </div>
          <div className="composer">
            <textarea
              rows={2} value={text} placeholder="Say something. Enter to send, Shift+Enter for a new line."
              disabled={busy !== null} onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            />
            <button className="btn" onClick={send} disabled={busy !== null || !text.trim()}>Send</button>
          </div>
        </div>
        <aside>
          <div className="side-card">
            <h3>Before the call</h3>
            <p className="small">{v.character.public_brief}</p>
            <p className="small muted"><strong>Your goal:</strong> {v.character.call_goal}</p>
          </div>
          <div className="side-card" style={{ marginTop: 12 }}>
            <h3>Talk time</h3>
            <div className={`meter ${ratio > 35 ? "over" : ""}`}><span style={{ width: `${Math.min(100, ratio)}%` }} /></div>
            <p className="small muted" style={{ margin: "6px 0 0" }}>
              You: {ratio}% of the words. In discovery, aim for 35% or less.
            </p>
            <p className="small muted" style={{ margin: "6px 0 0" }}>{v.fde_messages} of {v.max_messages} messages used</p>
          </div>
          <button className="btn" style={{ marginTop: 12, width: "100%" }} onClick={finish} disabled={busy !== null || v.fde_messages === 0}>
            {busy === "end" ? "Scoring… (about 30s)" : "End call & get debrief"}
          </button>
        </aside>
      </div>
    </>
  );
}

function DebriefView({ d }: { d: Debrief }) {
  return (
    <>
      <h1>Debrief: {d.character.name}</h1>
      <p className="lede">{d.scenario} · {d.duration_min} min</p>
      <div className="grid" style={{ marginBottom: 18 }}>
        <div className="card"><div className="score">{d.average}<span className="muted" style={{ fontSize: 16 }}> / 5</span></div><div className="small muted">average across 6 skills</div></div>
        <div className="card"><div className="score">{d.discovery_pct}%</div><div className="small muted">of what they knew, by importance, that you uncovered</div></div>
        <div className="card"><div className="score">{d.talk_ratio}%</div><div className="small muted">of the words were yours {d.talk_ratio <= 35 ? "(good)" : "(aim for 35% or less)"}</div></div>
      </div>
      <p>{d.verdict}</p>

      <h2>Skills</h2>
      <div className="dims">
        {d.dimensions.map((x) => (
          <div className="dim" key={x.name}>
            <div className="row"><strong>{x.name}</strong><div className="spacer" /><span className="n">{x.score}/5</span></div>
            <div className="small muted">{x.evidence}</div>
            <div className="small" style={{ marginTop: 4 }}><strong>Next time:</strong> {x.advice}</div>
          </div>
        ))}
      </div>

      <h2>Do these next time</h2>
      <ol>{d.next_time.map((t, i) => <li key={i}>{t}</li>)}</ol>

      <h2>What you uncovered</h2>
      {d.discovered.length ? d.discovered.map((f) => <div className="fact" key={f.id}>{f.fact}</div>) : <p className="muted">Nothing yet.</p>}

      <h2>What you missed</h2>
      {d.missed.length ? d.missed.map((f) => (
        <div className="fact miss" key={f.id}>
          {f.fact}
          {f.question && <div className="small muted" style={{ marginTop: 4 }}>Ask: <em>{f.question}</em></div>}
        </div>
      )) : <p className="muted">You found everything.</p>}

      <p className="small muted" style={{ marginTop: 24 }}>
        Saved to <code>{d.saved_as}</code>. Commit it: it&apos;s one of your discovery-call reps for PROGRESS.md.
      </p>
      <a className="btn ghost" href="/stakeholders" style={{ textDecoration: "none", display: "inline-block" }}>Another call</a>
    </>
  );
}
