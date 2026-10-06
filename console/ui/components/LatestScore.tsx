"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { RunSummary, sim } from "@/lib/sim";

export default function LatestScore({ lab, href, title }: { lab: string; href: string; title: string }) {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  useEffect(() => {
    sim<{ runs: RunSummary[] }>(`/checks/${lab}/runs`).then((r) => setRuns(r.runs)).catch(() => setRuns([]));
  }, [lab]);
  const last = runs?.at(-1);
  return (
    <Link href={href} className="card" style={{ textDecoration: "none", color: "inherit" }}>
      <h3>{title}</h3>
      {last ? (
        <>
          <div className="row">
            <span className="score">{Math.round((100 * last.score) / last.total)}%</span>
            <span className="muted small">{last.passed}/{last.count} checks · {runs!.length} runs</span>
          </div>
          <div className="bar"><span style={{ width: `${(100 * last.score) / last.total}%` }} /></div>
        </>
      ) : (
        <div className="muted small">{runs === null ? "…" : "No runs yet. Open the lab and read the contract."}</div>
      )}
    </Link>
  );
}
