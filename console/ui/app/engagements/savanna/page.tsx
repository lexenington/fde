import Markdown from "@/components/Markdown";
import SavannaTabs from "@/components/SavannaTabs";
import { readRepoFile } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function Savanna() {
  const world = await readRepoFile("04-engagements/savanna/WORLD.md");
  return (
    <>
      <h1>Engagement 2: Savanna Microfinance</h1>
      <p className="lede">
        A copilot for loan officers: policy answers that cite their source, member summaries, and an audit trail Risk can hand to the
        regulator. Their world: a 140-page policy amended by circulars, member data from three sources that disagree, a login system,
        and an acceptance test. You build the copilot; it runs on your machine.
      </p>
      <SavannaTabs world={world ? <Markdown source={world} /> : <div className="err">04-engagements/savanna/WORLD.md not found. Is the repo mounted?</div>} />
    </>
  );
}
