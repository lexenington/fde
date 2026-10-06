import LakesideTabs from "@/components/LakesideTabs";
import Markdown from "@/components/Markdown";
import { readRepoFile } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function Lakeside() {
  const world = await readRepoFile("04-engagements/lakeside/WORLD.md");
  return (
    <>
      <h1>Engagement 1: Lakeside Clinics</h1>
      <p className="lede">
        A WhatsApp assistant for 14 clinics. This is their world: a legacy booking database, a WhatsApp provider, a speech-to-text
        service, and a customer who will run an acceptance test before saying yes. You build the bot; it runs on your machine.
      </p>
      <LakesideTabs world={world ? <Markdown source={world} /> : <div className="err">04-engagements/lakeside/WORLD.md not found. Is the repo mounted?</div>} />
    </>
  );
}
