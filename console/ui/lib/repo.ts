import { readFile } from "node:fs/promises";
import path from "node:path";

// The repo root: mounted at /repo in Docker, two levels up from console/ui in `npm run dev`
const ROOT = process.env.REPO_DIR ?? path.resolve(process.cwd(), "..", "..");

export async function readRepoFile(rel: string): Promise<string | null> {
  try {
    // the repo is read at request time from a path the build can't know, so keep it out of the build trace
    const text = await readFile(path.join(/*turbopackIgnore: true*/ ROOT, /*turbopackIgnore: true*/ rel), "utf-8");
    // Git on Windows checks files out with CRLF; the parsers expect "\n" (in JS regex, "." doesn't match "\r")
    return text.replace(/\r\n/g, "\n");
  } catch {
    return null;
  }
}
