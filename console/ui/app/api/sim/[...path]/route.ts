// Proxies the browser to the customer simulator, so the UI works the same in Docker and in `npm run dev`.
const SIM = process.env.SIM_INTERNAL_URL ?? "http://localhost:8090";

async function proxy(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const url = new URL(req.url);
  const target = `${SIM}/${path.join("/")}${url.search}`;
  try {
    const res = await fetch(target, {
      method: req.method,
      headers: { "content-type": req.headers.get("content-type") ?? "application/json" },
      body: ["GET", "HEAD"].includes(req.method) ? undefined : await req.text(),
      cache: "no-store",
    });
    // pass bytes through untouched: documents (PDFs) must not be turned into text
    const headers: Record<string, string> = { "content-type": res.headers.get("content-type") ?? "application/json" };
    const disposition = res.headers.get("content-disposition");
    if (disposition) headers["content-disposition"] = disposition;
    return new Response(await res.arrayBuffer(), { status: res.status, headers });
  } catch {
    return Response.json({ detail: `simulator unreachable at ${SIM}` }, { status: 502 });
  }
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
