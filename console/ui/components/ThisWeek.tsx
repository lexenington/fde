"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Markdown from "@/components/Markdown";
import type { Phase, Week } from "@/lib/plan";

const MS_WEEK = 7 * 24 * 3600 * 1000;

export default function ThisWeek({ rhythm, weeks, rules, phases, started }: { rhythm: string; weeks: Week[]; rules: string; phases: Phase[]; started: string | null }) {
  const [start, setStart] = useState<string>(started ?? "");
  const [pick, setPick] = useState<number | null>(null);
  const [tab, setTab] = useState<"week" | "rhythm" | "rules">("week");

  useEffect(() => {
    if (started) return;       // a date written in PROGRESS.md wins
    try { setStart(localStorage.getItem("fde-start") ?? ""); } catch { /* storage can be unavailable */ }
  }, [started]);
  const save = (v: string) => { setStart(v); try { localStorage.setItem("fde-start", v); } catch { /* ignore */ } };

  const today = Date.now();
  const startMs = start ? new Date(start + "T00:00:00").getTime() : NaN;
  const elapsed = Number.isNaN(startMs) ? null : Math.floor((today - startMs) / MS_WEEK) + 1;
  const current = elapsed === null ? 1 : Math.min(Math.max(elapsed, 1), weeks.length);
  const n = pick ?? current;
  const week = weeks.find((w) => w.n === n) ?? weeks[0];
  const pct = (p: Phase) => Math.round((100 * p.done) / p.total);
  const done = phases.reduce((a, p) => a + p.done, 0), total = phases.reduce((a, p) => a + p.total, 0);

  return (
    <>
      <div className="card" style={{ marginBottom: 18 }}>
        <div className="row">
          <div>
            <div className="score">Week {current}<span className="muted" style={{ fontSize: 16 }}> of {weeks.length}</span></div>
            <div className="small muted">
              {elapsed === null ? "Set your start date to track the week."
                : elapsed > weeks.length ? `You're ${elapsed - weeks.length} week(s) past the plan. That's fine. Cut the stretch items.`
                : elapsed < 1 ? "Your start date is in the future." : `Started ${start}`}
            </div>
          </div>
          <div className="spacer" />
          {!started && <label className="small muted">I started on <input type="date" value={start} onChange={(e) => save(e.target.value)} /></label>}
          <div style={{ minWidth: 180 }}>
            <div className="small muted">{done} of {total} items ticked in PROGRESS.md</div>
            <div className="bar"><span style={{ width: `${total ? (100 * done) / total : 0}%` }} /></div>
          </div>
        </div>
      </div>

      <div className="tabs">
        <button className={tab === "week" ? "on" : ""} onClick={() => setTab("week")}>Week plan</button>
        <button className={tab === "rhythm" ? "on" : ""} onClick={() => setTab("rhythm")}>Weekly rhythm</button>
        <button className={tab === "rules" ? "on" : ""} onClick={() => setTab("rules")}>When life happens</button>
      </div>

      {tab === "week" && (
        <div className="call" style={{ gridTemplateColumns: "1fr 260px" }}>
          <div>
            <div className="row" style={{ marginBottom: 10 }}>
              <button className="btn ghost" disabled={n <= 1} onClick={() => setPick(n - 1)}>← Previous</button>
              <strong>Week {week.n}: {week.title}</strong>
              <button className="btn ghost" disabled={n >= weeks.length} onClick={() => setPick(n + 1)}>Next →</button>
              {pick !== null && pick !== current && <button className="btn ghost" onClick={() => setPick(null)}>Back to this week</button>}
            </div>
            <Markdown source={week.body} />
            <p className="small muted">Tick items in <code>PROGRESS.md</code> and commit. This page reads the repo, so a refresh shows what you ticked.</p>
          </div>
          <aside>
            <div className="side-card">
              <h3>Where you are</h3>
              {phases.map((p) => (
                <div key={p.title} style={{ marginBottom: 10 }}>
                  <div className="small">{p.title} <span className="muted">{p.done}/{p.total}</span></div>
                  <div className="bar"><span style={{ width: `${pct(p)}%` }} /></div>
                </div>
              ))}
            </div>
            <div className="side-card" style={{ marginTop: 12 }}>
              <h3>Tools</h3>
              <div className="small" style={{ display: "grid", gap: 4 }}>
                <Link href="/stakeholders">Stakeholder calls</Link>
                <Link href="/injects">Inject cards</Link>
                <Link href="/labs/integration">02/02 checker</Link>
                <Link href="/engagements/lakeside">Lakeside</Link>
                <Link href="/engagements/savanna">Savanna</Link>
              </div>
            </div>
          </aside>
        </div>
      )}
      {tab === "rhythm" && <Markdown source={rhythm} />}
      {tab === "rules" && <Markdown source={rules} />}
    </>
  );
}
