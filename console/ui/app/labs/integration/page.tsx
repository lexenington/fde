import LabRunner from "@/components/LabRunner";
import Markdown from "@/components/Markdown";
import { readRepoFile } from "@/lib/repo";

export const dynamic = "force-dynamic";

export default async function IntegrationLab() {
  const contract = await readRepoFile("02-technical-depth/02-enterprise-integration/lab/CONTRACT.md");
  return (
    <>
      <h1>02 Enterprise integration</h1>
      <p className="lede">
        Adom Logistics (2,000 staff) will only let RunMySales near production if it uses their IdP, respects their
        provisioning, and syncs with their CRM without losing or duplicating anything. Build it in your own app; this page
        drives your app through their systems and scores it. Hints appear for your first failure only. Fix it before
        reading the next one.
      </p>
      <LabRunner
        lab="integration"
        contract={contract ? <Markdown source={contract} /> : <div className="err">CONTRACT.md not found. Is the repo mounted?</div>}
      />
    </>
  );
}
