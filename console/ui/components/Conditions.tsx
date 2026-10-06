"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type C = { active: string[] };

/** Shows what inject cards have changed in the customer's systems, so a failing checker is never a mystery. */
export default function Conditions({ lab, link = true }: { lab: string; link?: boolean }) {
  const [c, setC] = useState<C | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = () => sim<C>("/admin/conditions").then(setC).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);
  if (!c?.active.length) return null;
  return (
    <div className="banner">
      <div className="row">
        <strong>The customer&apos;s systems have changed. Inject cards did this:</strong>
        <div className="spacer" />
        {link && <Link href="/injects">Open cards</Link>}
        <button className="btn ghost" onClick={() => sim(`/injects/${lab}/clear`, { method: "POST" }).then(load).catch((e) => setErr(e.message))}>
          Clear conditions
        </button>
      </div>
      <ul>{c.active.map((a) => <li key={a}>{a}</li>)}</ul>
      {err && <div className="small">{err}</div>}
    </div>
  );
}
