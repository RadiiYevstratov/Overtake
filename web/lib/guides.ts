/**
 * Evergreen guides — the indexed half of the SEO plan.
 *
 * League pages are noindex, so these carry the organic search work. Each one
 * answers a question the tool itself answers, from the rival-relative angle
 * nobody else writes from, and each links back into the product.
 */

export interface Guide {
  slug: string;
  href: string;
  title: string;
  metaTitle: string;
  description: string;
  lead: string;
  sections: { heading: string; body: string[] }[];
}

const HOW_TO: Guide[] = [
  {
    slug: "find-your-fpl-league-id",
    href: "/how-to/find-your-fpl-league-id",
    title: "How to find your FPL league ID",
    metaTitle: "How to find your FPL mini-league ID (30 seconds)",
    description:
      "Your FPL league ID is the number in the URL of your league's standings page. Here is exactly where to look on desktop and mobile.",
    lead: "It is the number in the URL of your league's standings page. Thirty seconds, and you never need it again.",
    sections: [
      {
        heading: "On a computer",
        body: [
          "Sign in to the Fantasy Premier League website and open the Leagues tab. Click the name of your mini-league to open its standings.",
          "Look at the address bar. The URL looks like fantasy.premierleague.com/leagues/123456/standings/c — the number in the middle, 123456, is your league ID.",
          "You can paste the whole URL into Overtake if you would rather not pick the number out. We will find it.",
        ],
      },
      {
        heading: "On the phone app",
        body: [
          "Open the league, tap the share icon, and copy the link. The link contains the same number.",
          "If the app will not give you a link, open fantasy.premierleague.com in your phone's browser instead and follow the desktop steps — the mobile site works fine.",
        ],
      },
      {
        heading: "What Overtake does with it",
        body: [
          "We read the league's public standings and every member's public squad from the official FPL API, then simulate the rest of the season to work out your probability of finishing above each of them.",
          "We never ask for your FPL password, and we have no write access to your team. The league ID on its own is enough, and it is not secret — anyone in your league already has it.",
        ],
      },
      {
        heading: "Which leagues work",
        body: [
          "Classic mini-leagues up to 200 managers. Overtake is built for leagues of people you actually know, so the giant public leagues and the global league are deliberately not supported — a probability against thirteen million strangers is not a fact anyone can use.",
          "Head-to-head leagues are not supported yet.",
        ],
      },
    ],
  },
  {
    slug: "find-your-fpl-manager-id",
    href: "/how-to/find-your-fpl-manager-id",
    title: "How to find your FPL manager ID",
    metaTitle: "How to find your FPL manager (entry) ID",
    description:
      "Your FPL manager ID is the number in your Points page URL. Here is how to find it in under a minute.",
    lead: "It is the number in your own Points page URL, and Overtake needs it to know which squad in the league is yours.",
    sections: [
      {
        heading: "Where to look",
        body: [
          "Sign in to the FPL website and open the Points tab. The URL reads fantasy.premierleague.com/entry/1234567/event/7 — the first number, 1234567, is your manager ID.",
          "It is sometimes called an entry ID. They are the same thing.",
        ],
      },
      {
        heading: "The easier way",
        body: [
          "You do not have to look it up. Open your league page on Overtake and pick your own name from the list — we will save the ID for you.",
        ],
      },
    ],
  },
];

const MINI_LEAGUE: Guide[] = [
  {
    slug: "how-to-win-your-fpl-mini-league",
    href: "/mini-league/how-to-win-your-fpl-mini-league",
    title: "How to win your FPL mini-league",
    metaTitle: "How to win your FPL mini-league (it is not by maximising points)",
    description:
      "Winning a mini-league is a different problem from maximising expected points. Here is what actually decides it, and when the standard advice is exactly wrong.",
    lead: "Every piece of FPL advice you have read optimises the wrong thing. Here is the right one.",
    sections: [
      {
        heading: "The mistake almost everyone makes",
        body: [
          "Expected points is the correct objective if your goal is a top-10k global finish. Almost nobody's goal is that. Your goal is finishing above eight named people, and those are mathematically different problems with different answers.",
          "The difference is largest exactly when you care most. If you are forty points behind with six gameweeks left, the highest-expected-points move is usually the move your rival is also making — so it changes nothing, and you finish forty points behind having played optimally.",
        ],
      },
      {
        heading: "Behind? You need variance, not points",
        body: [
          "When you are behind, you do not need to score well. You need to score differently. A player your rival owns cannot gain you anything on them, however many points he scores — you both get him.",
          "That means deliberately owning players your rivals do not, and captaining differentials rather than the safe pick. It will feel wrong, because every piece of content you read is written for the global-rank player. It is not wrong; it is the only lever you have.",
          "The cost is real: a differential captain that blanks costs you against the field. That is the trade, and it is worth making in proportion to how far behind you are.",
        ],
      },
      {
        heading: "Ahead? Do the exact opposite",
        body: [
          "Defending a lead is about removing your rivals' chances to gain, not creating your own. If the person chasing you owns a premium you do not, they gain every week he hauls and you can do nothing about it.",
          "So cover their differentials. Own what they own. Take the boring captain. A gameweek where you both score 60 is a gameweek you won, because there is one fewer left.",
          "This is the advice nobody publishes, because it is useless to someone chasing a global rank and it makes for bad content.",
        ],
      },
      {
        heading: "Chips are about timing, not value",
        body: [
          "A chip played in the same gameweek as your rival's chip buys you almost nothing against them. A chip played in a week they are exposed and you are not is worth double what the raw points say.",
          "If you are chasing, hold. If you are leading and the chaser plays a chip, playing yours the same week neutralises most of the swing they were buying.",
        ],
      },
      {
        heading: "Know when it is over",
        body: [
          "Sometimes the honest answer is that you cannot catch the leader, and the useful target is the person one place above you. Pretending otherwise wastes a season.",
          "This is the number Overtake exists to give you: not expected points, but the probability that you finish above each specific person, and what changes it.",
        ],
      },
    ],
  },
  {
    slug: "fpl-differentials-explained",
    href: "/mini-league/fpl-differentials-explained",
    title: "FPL differentials, properly explained",
    metaTitle: "FPL differentials explained — the only lever when you are behind",
    description:
      "A differential is not a low-owned player. It is a player your rivals do not own — and that distinction is the whole point.",
    lead: "Global ownership is the wrong number. What matters is ownership inside your league.",
    sections: [
      {
        heading: "The definition everyone gets wrong",
        body: [
          "A differential is usually defined as a player owned by under 5% or 10% of managers globally. That definition is nearly useless to you.",
          "What matters is whether the eight people in your mini-league own him. A player on 3% global ownership who happens to be in four of your rivals' squads is not a differential for you. A player on 40% ownership that none of your rivals have is.",
        ],
      },
      {
        heading: "Why they only matter when you are behind",
        body: [
          "Points from a player your rival also owns cancel out. They are noise in the gap between you. Only the players you own and they do not can actually move it.",
          "So the value of a differential scales with how far behind you are. Level with someone? A differential is a coin flip you did not need to take. Forty points behind with six gameweeks left? It is the only thing that can close the gap in time.",
        ],
      },
      {
        heading: "How to pick one",
        body: [
          "Not by ownership alone, and not by upside alone. The right differential is the one with the best combination of expected points and low ownership among the specific people you are chasing.",
          "Fixtures matter more here than usual, because you are buying a short burst of separation rather than a season-long hold.",
        ],
      },
      {
        heading: "The honest downside",
        body: [
          "Differentials lose more often than they win. That is what makes them differentials. The reason to take them anyway is that a strategy which loses slowly and reliably still loses — and copying the template when you are behind is exactly that strategy.",
        ],
      },
    ],
  },
  {
    slug: "fpl-captaincy-strategy",
    href: "/mini-league/fpl-captaincy-strategy",
    title: "FPL captaincy when you are chasing someone",
    metaTitle: "FPL captain strategy for mini-leagues — when to go differential",
    description:
      "Captaincy is the biggest single lever you have each week. Whether to take the safe pick depends entirely on whether you are ahead or behind.",
    lead: "The captain doubles one player's score. Against a named rival, that is the cheapest way to create or remove variance.",
    sections: [
      {
        heading: "It costs nothing, which is what makes it the best lever",
        body: [
          "A transfer costs money or a hit. A chip is once a season. Captaincy is free and available every single week, and it is the decision with the largest spread of outcomes.",
        ],
      },
      {
        heading: "If your rival captains the same player",
        body: [
          "Nothing happens. Whatever he scores, you both get double. The gap between you is unchanged, which is fine if you are ahead and useless if you are behind.",
        ],
      },
      {
        heading: "The rule",
        body: [
          "Behind: captain someone they do not. The bigger the gap and the fewer the gameweeks, the more aggressive that choice should be.",
          "Ahead: captain what they captain. Matching removes their chance to gain, which is the entire job when you are defending.",
          "Level: take the highest expected points, because there is nothing to engineer.",
        ],
      },
      {
        heading: "State the downside before you commit",
        body: [
          "The right way to think about a differential captain is not 'how many points could this win me' but 'how many does it cost if he blanks and their pick hauls'. If you cannot say that number out loud, you are gambling rather than deciding.",
          "Overtake states it for you: the probability before, the probability after, and the cost if it goes wrong.",
        ],
      },
    ],
  },
];

export const GUIDES: Guide[] = [...HOW_TO, ...MINI_LEAGUE];

export function findGuide(prefix: "how-to" | "mini-league", slug: string): Guide | null {
  return (
    GUIDES.find((guide) => guide.href === `/${prefix}/${slug}`) ?? null
  );
}

export function guidesFor(prefix: "how-to" | "mini-league"): Guide[] {
  return GUIDES.filter((guide) => guide.href.startsWith(`/${prefix}/`));
}
