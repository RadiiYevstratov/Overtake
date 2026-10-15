import { expect, test } from "@playwright/test";

import { shareOrCopy, shareUrl } from "@/lib/share";

const payload = { title: "Overtake", text: "I'm 71% to finish above Dan in The Lads.", url: "" };

function environment(overrides: {
  share?: (data: unknown) => Promise<void>;
  writeText?: (text: string) => Promise<void>;
}) {
  const log = { shared: 0, copied: [] as string[], prompted: [] as string[] };
  return {
    log,
    env: {
      share: overrides.share
        ? async (data: { title: string; text: string; url: string }) => {
            await overrides.share!(data);
            log.shared += 1;
          }
        : undefined,
      writeText:
        overrides.writeText === undefined
          ? async (text: string) => {
              log.copied.push(text);
            }
          : overrides.writeText,
      prompt: (_message: string, value: string) => {
        log.prompted.push(value);
      },
    },
  };
}

function domError(name: string) {
  const error = new Error(name);
  error.name = name;
  return error;
}

test.describe("the share link", () => {
  test("names nobody, so the recipient is never shown as the sharer", () => {
    const url = new URL(shareUrl("https://overtakefpl.com", 1757));
    expect(url.pathname).toBe("/l/1757");
    expect(url.searchParams.has("entry")).toBe(false);
    expect(url.searchParams.has("you")).toBe(false);
    expect(url.searchParams.get("utm_source")).toBe("share");
  });
});

test.describe("sharing", () => {
  test("uses the native share sheet when there is one", async () => {
    const { env, log } = environment({ share: async () => {} });
    expect(await shareOrCopy(payload, env)).toBe("shared");
    expect(log.shared).toBe(1);
    expect(log.copied).toEqual([]);
  });

  test("cancelling the share sheet does nothing else — no clipboard write", async () => {
    const { env, log } = environment({
      share: async () => {
        throw domError("AbortError");
      },
    });
    expect(await shareOrCopy(payload, env)).toBe("cancelled");
    expect(log.copied).toEqual([]);
    expect(log.prompted).toEqual([]);
  });

  test("a platform that refuses the data falls back to the clipboard", async () => {
    const { env, log } = environment({
      share: async () => {
        throw domError("NotAllowedError");
      },
    });
    expect(await shareOrCopy(payload, env)).toBe("copied");
    expect(log.copied).toHaveLength(1);
  });

  test("without native sharing it copies the message and the link", async () => {
    const { env, log } = environment({});
    const outcome = await shareOrCopy({ ...payload, url: "https://overtakefpl.com/l/1" }, env);
    expect(outcome).toBe("copied");
    expect(log.copied).toEqual([`${payload.text}\nhttps://overtakefpl.com/l/1`]);
  });

  test("with no clipboard either it offers the text to copy by hand", async () => {
    const { env, log } = environment({
      writeText: async () => {
        throw domError("NotAllowedError");
      },
    });
    expect(await shareOrCopy(payload, env)).toBe("prompted");
    expect(log.prompted).toHaveLength(1);
  });
});
