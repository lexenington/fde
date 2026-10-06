import Health from "@/components/Health";
import LatestScore from "@/components/LatestScore";

export default function Dashboard() {
  return (
    <>
      <h1>Dashboard</h1>
      <p className="lede">
        This stack plays the customer. Your code lives in the lab folders and runs on your machine; the Console drives it
        through the customer&apos;s systems and scores it. It never writes your solution.
      </p>
      <a className="card" href="/plan" style={{ textDecoration: "none", color: "inherit", display: "block", marginBottom: 14 }}>
        <strong>This week →</strong>
        <div className="small muted">What to do now, from the 16-week plan, with your progress.</div>
      </a>
      <Health />

      <h2>Labs</h2>
      <div className="grid">
        <LatestScore lab="integration" href="/labs/integration" title="02 Enterprise integration" />
        <div className="card">
          <h3>01 Messy data</h3>
          <div className="small muted">Terminal for now: <code>python check.py out/clusters.json</code></div>
        </div>
        <div className="card">
          <h3>03 AI engineering</h3>
          <div className="small muted">Terminal for now: <code>python eval.py</code></div>
        </div>
      </div>

      <h2>Practice</h2>
      <div className="grid">
        <a className="card" href="/stakeholders" style={{ textDecoration: "none", color: "inherit" }}>
          <h3>Stakeholder calls</h3>
          <div className="small muted">Ten people across three customers, played by Claude. They only tell you what you ask well for. Scored debrief and a saved transcript.</div>
        </a>
        <a className="card" href="/injects" style={{ textDecoration: "none", color: "inherit" }}>
          <h3>Inject cards</h3>
          <div className="small muted">Mid-lab curveballs: quota cuts, late webhooks, secret rotation, an IdP change. Handle them in code, then write the reply.</div>
        </a>
      </div>

      <h2>A working session</h2>
      <ol className="small">
        <li>Read the lab contract. Write <code>SCOPE.md</code> before code.</li>
        <li>Build one capability, then run the checker. Read the hint on the first failure only.</li>
        <li>Poke the CRM by hand: change a stage, add a note, turn on 429s. Watch what your app does.</li>
        <li>Commit, including the run file in <code>lab/runs/</code>. The history of scores is your evidence.</li>
      </ol>
    </>
  );
}
