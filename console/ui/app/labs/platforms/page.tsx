import LabRunner from "@/components/LabRunner";
import Markdown from "@/components/Markdown";
import { readRepoFile } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function PlatformsLab() {
  const contract = await readRepoFile("02-technical-depth/06-enterprise-platforms/lab/CONTRACT.md");
  return (
    <>
      <h1>02/06 Enterprise platforms</h1>
      <p className="lede">
        Volta Industrial Supplies runs ServiceNow for IT and SAP for orders. Your agent&apos;s tool layer has to create and update their
        incidents and read and hold their sales orders, without making duplicates, losing pages of data or crashing when either system has a bad
        day. The checks play the model and make the tool calls; they then look inside both systems to see what really happened. Watch it live on
        the <a href="/systems/platforms">ServiceNow &amp; SAP</a> page.
      </p>
      <LabRunner
        lab="platforms"
        contract={contract ? <Markdown source={contract} /> : <div className="err">CONTRACT.md not found. Is the repo mounted?</div>}
      />
    </>
  );
}
