export const runtime = "edge";

const BACKEND = process.env.BACKEND_URL;

async function proxy(req: Request, segments: string[]): Promise<Response> {
  if (!BACKEND) {
    return Response.json({ detail: "Backend not configured" }, { status: 503 });
  }

  const url = `${BACKEND}/api/v1/${segments.join("/")}`;
  const ct = req.headers.get("content-type");
  const headers = new Headers();
  if (ct) headers.set("content-type", ct);

  const hasBody = req.method !== "GET" && req.method !== "HEAD";

  const upstream = await fetch(url, {
    method: req.method,
    headers,
    ...(hasBody ? { body: req.body, duplex: "half" } : {}),
  } as RequestInit);

  const resHeaders = new Headers();
  const resCt = upstream.headers.get("content-type");
  if (resCt) resHeaders.set("content-type", resCt);

  return new Response(upstream.body, {
    status: upstream.status,
    headers: resHeaders,
  });
}

export async function GET(
  req: Request,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params.path);
}

export async function POST(
  req: Request,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params.path);
}
