import { readRepoFile } from "@/lib/repo";

export type Week = { n: number; title: string; body: string };
export type Phase = { title: string; done: number; total: number };

/** Split PLAN.md by its "## " sections: the weekly rhythm, one entry per "## Week N: title", and "When life happens". */
export function parsePlan(md: string): { intro: string; rhythm: string; weeks: Week[]; rules: string } {
  const parts = md.split(/\n(?=## )/);
  const weeks: Week[] = [];
  let rhythm = "", rules = "";
  for (const p of parts.slice(1)) {
    const w = p.match(/^## Week (\d+): (.+)\n([\s\S]*)$/);
    if (w) {
      weeks.push({ n: +w[1], title: w[2].trim(), body: w[3].replace(/\n---\s*$/, "").trim() });
    } else if (/^## The weekly rhythm/.test(p)) {
      rhythm = p.replace(/^## .*\n/, "").replace(/\n---\s*$/, "").trim();
    } else if (/^## When life happens/.test(p)) {
      rules = p.replace(/^## .*\n/, "").trim();
    }
  }
  return { intro: parts[0], rhythm, weeks, rules };
}

/** Count `[ ]` / `[x]` per "## " section of PROGRESS.md, including everything under its "### " sub-sections. */
export function parseProgress(raw: string): { phases: Phase[]; started: string | null } {
  const md = raw.replace(/<!--[\s\S]*?-->/g, "");        // comments may contain example dates and checkboxes
  const phases: Phase[] = [];
  let cur: Phase | null = null;
  for (const line of md.split("\n")) {
    const h = line.match(/^## (.+)/);
    if (h) { cur = { title: h[1].trim(), done: 0, total: 0 }; phases.push(cur); continue; }
    if (!cur) continue;
    for (const m of line.matchAll(/\[( |x|X)\]|☐|☑/g)) {
      cur.total += 1;
      if (m[1] === "x" || m[1] === "X" || m[0] === "☑") cur.done += 1;
    }
  }
  const s = md.match(/Started:\s*(\d{4}-\d{2}-\d{2})/);
  return { phases: phases.filter((p) => p.total > 0), started: s ? s[1] : null };
}

export async function loadPlan() {
  const [plan, progress] = await Promise.all([readRepoFile("PLAN.md"), readRepoFile("PROGRESS.md")]);
  return {
    plan: plan ? parsePlan(plan) : null,
    progress: progress ? parseProgress(progress) : null,
  };
}
