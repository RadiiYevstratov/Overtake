import { expect, test } from "@playwright/test";

import {
  chaseVerb,
  leagueIdError,
  neededPerGw,
  parseLeagueId,
  standing,
} from "@/lib/format";

test.describe("needed per gameweek", () => {
  test("renders the API's figure, never recomputes it from the gap", () => {
    expect(neededPerGw(2.65)).toBe("+2.6");
    expect(neededPerGw(0.12)).toBe("+0.1");
    expect(neededPerGw(0.02)).toBe("+<0.1");
  });

  test("zero means already favourite; null means no gameweeks left", () => {
    expect(neededPerGw(0)).toBe("On course");
    expect(neededPerGw(null)).toBe("—");
    expect(neededPerGw(undefined)).toBe("—");
  });
});

test.describe("wording by where you stand", () => {
  test("a rival ahead is caught, one behind is held off, a level one is beaten", () => {
    // gap_now is you minus them.
    expect(standing(-12)).toBe("behind");
    expect(standing(13)).toBe("ahead");
    expect(standing(0)).toBe("level");
    expect(chaseVerb(-12, "Geir")).toBe("catch Geir");
    expect(chaseVerb(13, "Jonny Currie")).toBe("stay ahead of Jonny Currie");
    expect(chaseVerb(0, "Dan")).toBe("finish above Dan");
  });
});

test.describe("league ID input", () => {
  test("empty and whitespace-only input get their own message", () => {
    expect(parseLeagueId("")).toBeNull();
    expect(parseLeagueId("   ")).toBeNull();
    expect(leagueIdError("")).toMatch(/paste your league id/i);
    expect(leagueIdError("   ")).toMatch(/paste your league id/i);
  });

  test("malformed input is told it is not a league ID", () => {
    expect(parseLeagueId("hello world")).toBeNull();
    expect(leagueIdError("hello world")).toMatch(/does not look like a league id/i);
  });

  test("valid ids and FPL URLs are accepted", () => {
    expect(parseLeagueId("1757")).toBe(1757);
    expect(parseLeagueId(" 1757 ")).toBe(1757);
    expect(parseLeagueId("https://fantasy.premierleague.com/leagues/1757/standings/c")).toBe(1757);
  });
});
