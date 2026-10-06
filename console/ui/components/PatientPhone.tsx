"use client";

import { useEffect, useRef, useState } from "react";
import { sim } from "@/lib/sim";

type M = { dir: "in" | "out"; id: string; at: number; kind: string; body: string; template?: string };
type Timeline = { phone: string; messages: M[]; window_open: boolean };
type Note = { id: string; label: string; transcript: string; confidence: number };

export default function PatientPhone() {
  const [phone, setPhone] = useState("+233201230001");
  const [t, setT] = useState<Timeline | null>(null);
  const [text, setText] = useState("");
  const [notes, setNotes] = useState<Note[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [hooks, setHooks] = useState<{ at: string; type: string; status: number | null; error?: string }[]>([]);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { sim<Note[]>("/lakeside/voicenotes").then(setNotes).catch(() => {}); }, []);
  useEffect(() => {
    const load = () => {
      sim<Timeline>(`/lakeside/phone/${encodeURIComponent(phone)}`).then(setT).catch((e) => setErr(e.message));
      sim<typeof hooks>("/lakeside/webhooks").then(setHooks).catch(() => {});
    };
    load();
    const i = setInterval(load, 1500);
    return () => clearInterval(i);
  }, [phone]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [t?.messages.length]);

  const send = async (p: Promise<unknown>) => { setErr(null); try { await p; } catch (e) { setErr((e as Error).message); } };
  const clock = (s: number) => new Date(s * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  return (
    <div className="two">
      <div>
        <div className="phone">
          <div className="phone-top">
            <div><div>Lakeside Clinics</div><div className="small">you are {phone}</div></div>
            <div className="small">{t?.window_open ? "24h window open" : "window closed"}</div>
          </div>
          <div className="wa">
            {t?.messages.map((m) => (
              <div key={m.id + m.at} className={`m ${m.dir}`}>
                {m.kind === "template" && <div className="tpl">template: {m.template}</div>}
                {m.kind === "audio" ? "🎤 voice note" : m.body}
                <div className="t">{clock(m.at)}</div>
              </div>
            ))}
            {t && !t.messages.length && <div className="small muted" style={{ textAlign: "center", marginTop: 40 }}>Say hello as a patient. Your bot&apos;s replies appear here.</div>}
            <div ref={end} />
          </div>
          <form className="phone-in" onSubmit={(e) => { e.preventDefault(); if (text.trim()) { send(sim(`/lakeside/phone/${encodeURIComponent(phone)}/text`, { json: { text } })); setText(""); } }}>
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a message" />
            <button className="btn" disabled={!text.trim()}>Send</button>
          </form>
        </div>
        {err && <div className="err">{err}</div>}
      </div>

      <div>
        <h3 style={{ marginTop: 0 }}>You are the patient</h3>
        <p className="small muted">
          Messages you send reach your bot at <code>/webhooks/whatsapp</code>, signed like the real provider&apos;s. Replies appear in the phone once your bot calls the send API.
        </p>
        <div className="row" style={{ marginBottom: 10 }}>
          <label className="small">Your number <input value={phone} onChange={(e) => setPhone(e.target.value.trim())} style={{ width: 170 }} /></label>
          <button className="btn ghost" onClick={() => send(sim(`/lakeside/phone/${encodeURIComponent(phone)}/age`, { method: "POST" }))}
            title="Pretend the patient last wrote 25 hours ago: free text is no longer allowed, only approved templates">Make the 24h window expire</button>
        </div>
        <h3>Voice notes</h3>
        <p className="small muted">Real audio isn&apos;t simulated. Each note arrives as a media id; your bot fetches it and transcribes it with the speech-to-text service, which returns the transcript below and a confidence score.</p>
        {notes.map((n) => (
          <div key={n.id} className="row" style={{ marginBottom: 6 }}>
            <button className="btn ghost" onClick={() => send(sim(`/lakeside/phone/${encodeURIComponent(phone)}/voice`, { json: { note: n.id } }))}>🎤 {n.label}</button>
            <span className="small muted">confidence {n.confidence}</span>
          </div>
        ))}
        <h3>What your bot answered</h3>
        <div className="table-wrap" style={{ maxHeight: 220, overflowY: "auto" }}>
          <table>
            <thead><tr><th>At</th><th>Event</th><th>Your app said</th></tr></thead>
            <tbody>
              {hooks.slice(0, 15).map((h, i) => (
                <tr key={i}><td className="small">{h.at}</td><td className="small">{h.type}</td>
                  <td>{h.status ? <span className={`pill ${h.status < 300 ? "pass" : "fail"}`}>{h.status}</span> : <span className="pill fail">{h.error ?? "no answer"}</span>}</td></tr>
              ))}
              {!hooks.length && <tr><td colSpan={3} className="muted">No webhook calls yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
