import ThisWeek from "@/components/ThisWeek";
import { loadPlan } from "@/lib/plan";

export const dynamic = "force-dynamic";

export default async function Plan() {
  const { plan, progress } = await loadPlan();
  return (
    <>
      <h1>This week</h1>
      <p className="lede">What to do now, from <code>PLAN.md</code>, with your progress from <code>PROGRESS.md</code>.</p>
      {plan && plan.weeks.length ? (
        <ThisWeek rhythm={plan.rhythm} weeks={plan.weeks} rules={plan.rules} phases={progress?.phases ?? []} started={progress?.started ?? null} />
      ) : (
        <div className="err">PLAN.md not found. Is the repo mounted?</div>
      )}
    </>
  );
}
