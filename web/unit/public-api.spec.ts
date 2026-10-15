import { expect, test } from "@playwright/test";

import { ApiError, isTransientStatus, supportReference } from "@/lib/api";
import { fetchPublic } from "@/lib/public-api";

/** A scripted API: each call takes the next response (or throws the next error). */
function scripted(...steps: (Response | Error)[]) {
  const calls: { url: string; init: RequestInit }[] = [];
  const fetcher = async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    const step = steps.shift();
    if (!step) throw new Error("no more scripted responses");
    if (step instanceof Error) throw step;
    return step;
  };
  return { fetcher, calls };
}

function json(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

const noSleep = async () => {};

test.describe("which failures are transient", () => {
  test("rate limits, server errors and no answer at all are transient", () => {
    for (const status of [0, 408, 429, 500, 502, 503, 504]) {
      expect(isTransientStatus(status), String(status)).toBe(true);
    }
  });

  test("a confirmed miss or a refusal is not", () => {
    for (const status of [400, 401, 402, 403, 404, 422, 425]) {
      expect(isTransientStatus(status), String(status)).toBe(false);
    }
  });
});

test.describe("fetchPublic", () => {
  test("returns the data for an existing resource", async () => {
    const { fetcher } = scripted(json(200, { player: { slug: "phil-foden" } }));
    const data = await fetchPublic<{ player: { slug: string } }>("/players/phil-foden", {}, {
      fetcher,
      sleep: noSleep,
    });
    expect(data.player.slug).toBe("phil-foden");
  });

  test("a confirmed missing player is a 404, and only that is not-found", async () => {
    const { fetcher } = scripted(
      json(404, { error: { code: "NOT_FOUND", message: "We do not have a page for that player." } }),
    );
    const error = await fetchPublic("/players/nobody", {}, { fetcher, sleep: noSleep }).catch(
      (e: unknown) => e,
    );
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).isNotFound).toBe(true);
    expect((error as ApiError).isTransient).toBe(false);
  });

  test("a 429 is transient, never not-found", async () => {
    const { fetcher, calls } = scripted(
      json(429, { error: { code: "RATE_LIMITED", message: "Slow down." } }, { "Retry-After": "41" }),
    );
    const error = (await fetchPublic("/players/phil-foden", {}, { fetcher, sleep: noSleep }).catch(
      (e: unknown) => e,
    )) as ApiError;
    expect(error.status).toBe(429);
    expect(error.isTransient).toBe(true);
    expect(error.isNotFound).toBe(false);
    expect(calls).toHaveLength(1); // a long Retry-After is not waited out inside a render
  });

  test("a 429 with a short Retry-After is retried once and then succeeds", async () => {
    const waits: number[] = [];
    const { fetcher, calls } = scripted(
      json(429, { error: { code: "RATE_LIMITED" } }, { "Retry-After": "1" }),
      json(200, { ok: true }),
    );
    const data = await fetchPublic<{ ok: boolean }>("/players/phil-foden", {}, {
      fetcher,
      sleep: async (ms) => {
        waits.push(ms);
      },
    });
    expect(data.ok).toBe(true);
    expect(calls).toHaveLength(2);
    expect(waits).toEqual([1000]);
  });

  test("it is retried at most once", async () => {
    const { fetcher, calls } = scripted(
      json(429, { error: { code: "RATE_LIMITED" } }, { "Retry-After": "1" }),
      json(429, { error: { code: "RATE_LIMITED" } }, { "Retry-After": "1" }),
    );
    const error = (await fetchPublic("/x", {}, { fetcher, sleep: noSleep }).catch(
      (e: unknown) => e,
    )) as ApiError;
    expect(error.status).toBe(429);
    expect(calls).toHaveLength(2);
  });

  test("a 5xx is transient", async () => {
    const { fetcher } = scripted(new Response("upstream down", { status: 503 }));
    const error = (await fetchPublic("/x", {}, { fetcher, sleep: noSleep }).catch(
      (e: unknown) => e,
    )) as ApiError;
    expect(error.status).toBe(503);
    expect(error.isTransient).toBe(true);
  });

  test("a refused connection is transient, with status 0", async () => {
    const { fetcher } = scripted(new TypeError("fetch failed"));
    const error = (await fetchPublic("/x", {}, { fetcher, sleep: noSleep }).catch(
      (e: unknown) => e,
    )) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.code).toBe("UPSTREAM_UNREACHABLE");
    expect(error.isTransient).toBe(true);
  });

  test("a hung API times out as transient", async () => {
    const hang = (_url: string, init: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init.signal?.addEventListener("abort", () => reject(init.signal?.reason));
      });
    const error = (await fetchPublic("/x", {}, { fetcher: hang, sleep: noSleep, timeoutMs: 20 }).catch(
      (e: unknown) => e,
    )) as ApiError;
    expect(error.code).toBe("UPSTREAM_TIMEOUT");
    expect(error.isTransient).toBe(true);
  });

  test("the visitor's identity is forwarded and no cookie is ever sent", async () => {
    const { fetcher, calls } = scripted(json(200, {}));
    await fetchPublic("/meta/season", { "X-Overtake-Client-IP": "203.0.113.9" }, {
      fetcher,
      sleep: noSleep,
    });
    const headers = calls[0]!.init.headers as Record<string, string>;
    expect(headers["X-Overtake-Client-IP"]).toBe("203.0.113.9");
    expect(Object.keys(headers).map((h) => h.toLowerCase())).not.toContain("cookie");
    expect(calls[0]!.init.cache).toBe("no-store");
  });
});

test.describe("support references", () => {
  test("an expected limit carries no reference to quote", () => {
    const limit = new ApiError(422, "LEAGUE_TOO_LARGE", "Too big", "abc123");
    expect(supportReference(limit)).toBeUndefined();
  });

  test("an unexpected failure keeps its reference", () => {
    expect(supportReference(new ApiError(500, "INTERNAL", "Boom", "abc123"))).toBe("abc123");
    expect(supportReference(new ApiError(429, "RATE_LIMITED", "Slow", "def456"))).toBe("def456");
  });
});
