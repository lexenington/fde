import { readFile } from "node:fs/promises";
import path from "node:path";

// The repo root: mounted at /repo in Docker, two levels up from console/ui in `npm run dev`
const ROOT = process.env.REPO_DIR ?? path.resolve(process.cwd(), "..", "..");

export async function readRepoFile(rel: string): Promise<string | null> {
  try {
    return await readFile(path.join(ROOT, rel), "utf-8");
  } catch {
    return null;
  }
}
