"use client";

import { useEffect, useState } from "react";
import { sim } from "@/lib/sim";

type H = { sim: boolean; keycloak: boolean; learner: { ok: boolean; status?: number; url: string; error?: string } };

export default function Health() {
  const [h, setH] = useState<H | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const load = () => sim<H>("/admin/health").then((x) => { setH(x); setErr(null); }).catch((e) => setErr(e.message));
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const dot = (ok: boolean | undefined) => <span className={`dot ${ok === undefined ? "wait" : ok ? "ok" : "bad"}`} />;
  return (
    <div className="grid">
      <div className="card">
        <h3>{dot(err ? false : h?.sim)}Customer simulator</h3>
        <div className="small muted">{err ?? "CRM API on localhost:8090/crm/v3, checkers, admin"}</div>
      </div>
      <div className="card">
        <h3>{dot(err ? false : h?.keycloak)}Customer IdP (Keycloak)</h3>
        <div className="small muted">
          {h && !h.keycloak ? "Starting up (takes ~30s on first boot)…" : "Realm adom on localhost:8081"}
        </div>
      </div>
      <div className="card">
        <h3>{dot(err ? false : h?.learner.ok)}Your app</h3>
        <div className="small muted">
          {h?.learner.ok ? `${h.learner.url} is answering` : `Not reachable at ${h?.learner.url ?? "…"}. Start it, or change the URL on the CRM page.`}
        </div>
      </div>
    </div>
  );
}
