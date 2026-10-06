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
