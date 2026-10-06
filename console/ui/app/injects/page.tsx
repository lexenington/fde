"use client";

import { useEffect, useState } from "react";
import Conditions from "@/components/Conditions";
import Markdown from "@/components/Markdown";
import { RunSummary, sim } from "@/lib/sim";

const LAB = "integration";

type Check = { name: string; ok: boolean; detail: string };
type Action = { at: string; passed: boolean | null; checks: Check[]; blocked: string | null };
type Card = {
  id: string; title: string; from: string; subject: string; body: string; drawn_at: string;
  response: string | null; feedback: { rating: number; what_works: string[]; fix_next: string[]; sharper_sentence: string } | null;
  actions: Action[]; has_hint: boolean; has_effect: boolean; hint: string | null; deliverable_prompt: string;
  action: { id: string; label: string; help: string } | null;
};
type Deck = { title: string; total: number; remaining: number; drawn: Card[] };

export default function Injects() {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = () => sim<Deck>(`/injects/${LAB}`).then(setDeck).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  async function draw() {
    setErr(null);
    try {
      const runs = (await sim<{ runs: RunSummary[] }>(`/checks/${LAB}/runs`)).runs;
      const last = runs.at(-1);
      const p = last ? Math.round((100 * last.score) / last.total) : 0;
      if (p < 50 && !confirm(`Your latest checker score is ${p}%. Cards land best once the basics work (50%+). Draw anyway?`)) return;
    } catch { /* checker history is optional */ }
    setBusy(true);
    try { await sim(`/injects/${LAB}/draw`, { method: "POST" }); await load(); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <>
      <h1>Inject cards</h1>
      <p className="lede">
        Real engagements don&apos;t hold still. Once your lab passes about half the checks, draw a card: an email lands, and
        sometimes the customer&apos;s systems change underneath you. Handle it in your code, then write the reply you&apos;d actually
        send. Replies and results are saved in <code>lab/injects/</code> for your commit history.
      </p>
      <Conditions lab={LAB} link={false} />
      {err && <div className="err">{err}</div>}

      <div className="row" style={{ marginBottom: 18 }}>
        <button className="btn" onClick={draw} disabled={busy || deck?.remaining === 0}>{busy ? "Drawing…" : "Draw a card"}</button>
        <span className="muted small">{deck ? `${deck.total - deck.remaining} of ${deck.total} drawn · ${deck.title}` : ""}</span>
      </div>

      {deck?.drawn.slice().reverse().map((c) => <CardView key={c.id} c={c} reload={load} />)}
      {deck && !deck.drawn.length && <p className="muted">No cards yet.</p>}
    </>
  );
}

function CardView({ c, reload }: { c: Card; reload: () => void }) {
  const [reply, setReply] = useState(c.response ?? "");
  const [busy, setBusy] = useState<"reply" | "action" | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const last = c.actions.at(-1);

  const run = async (kind: "reply" | "action", p: () => Promise<unknown>) => {
    setBusy(kind); setErr(null);
    try { await p(); } catch (e) { setErr((e as Error).message); }
    try { await reload(); } finally { setBusy(null); }
  };

  return (
    <div className="mail">
      <div className="mail-head">
        <div className="small muted">From: {c.from}</div>
        <strong>{c.subject}</strong>
      </div>
      <div className="mail-body"><Markdown source={c.body} /></div>
      <div className="mail-foot">
        {c.action && (
          <>
            <div className="row">
              <button className="btn ghost" disabled={busy !== null} onClick={() => run("action", () => sim(`/injects/${LAB}/cards/${c.id}/action`, { method: "POST" }))}>
                {busy === "action" ? "Running…" : c.action.label}
              </button>
              {c.has_hint && !c.hint && (
                <button className="btn ghost" onClick={() => run("action", () => sim(`/injects/${LAB}/cards/${c.id}/hint`, { method: "POST" }))}>I&apos;m stuck: what would I see?</button>
              )}
            </div>
            <p className="small muted">{c.action.help}</p>
            {c.hint && <p className="small"><strong>Symptom:</strong> {c.hint}</p>}
            {last && (
              <div style={{ margin: "8px 0 14px" }}>
                <span className={`pill ${last.passed === true ? "pass" : last.passed === false ? "fail" : "warn"}`}>
                  {last.passed === true ? "passed" : last.passed === false ? "failed" : "blocked"}
                </span>
                {last.blocked && <div className="small" style={{ marginTop: 4 }}>{last.blocked}</div>}
                {last.checks.map((k, i) => (
                  <div className="check" key={i}>
                    <span className={`pill ${k.ok ? "pass" : "fail"}`}>{k.ok ? "ok" : "fail"}</span> {k.name}
                    <div className="small muted" style={{ marginLeft: 46 }}>{k.detail}</div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {c.has_effect && (
          <p className="small muted">
            This card changed the customer&apos;s systems. If the simulator restarted, the change is gone:{" "}
            <a href="#" onClick={(e) => { e.preventDefault(); run("action", () => sim(`/injects/${LAB}/cards/${c.id}/reapply`, { method: "POST" })); }}>re-apply it</a>.
          </p>
        )}
        <div className="small" style={{ marginBottom: 6 }}><strong>Your task:</strong> {c.deliverable_prompt}</div>
        <textarea className="reply" value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Write the reply you would actually send…" />
        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn" disabled={busy !== null || reply.trim().length < 20}
            onClick={() => run("reply", () => sim(`/injects/${LAB}/cards/${c.id}/reply`, { json: { text: reply } }))}>
            {busy === "reply" ? "Reviewing…" : c.feedback ? "Review again" : "Get feedback"}
          </button>
        </div>
        {err && <div className="err">{err}</div>}
        {c.feedback && (
          <div className="card" style={{ marginTop: 12 }}>
            <div className="row"><strong>Feedback</strong><div className="spacer" /><span className="score" style={{ fontSize: 22 }}>{c.feedback.rating}/5</span></div>
            <ul className="small">
              {c.feedback.what_works.map((x, i) => <li key={`w${i}`}>Works: {x}</li>)}
              {c.feedback.fix_next.map((x, i) => <li key={`f${i}`}>Fix: {x}</li>)}
            </ul>
            <div className="small muted">Sharper: <em>{c.feedback.sharper_sentence}</em></div>
          </div>
        )}
      </div>
    </div>
  );
}
