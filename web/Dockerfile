# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# The Overtake web app. Built from web/ as the context, so this Dockerfile and
# web/fly.toml sit together and neither has to reach outside its own directory.
# ---------------------------------------------------------------------------

# Node 20 went end-of-life in April 2026; 22 is the supported LTS and satisfies
# the ">=20" engines constraint in package.json.
FROM node:22-slim AS deps
WORKDIR /srv/overtake
COPY package.json package-lock.json ./
# `npm ci` rather than `npm install`: the lockfile is the build input, and a
# deploy must never silently resolve a different dependency tree than CI tested.
RUN npm ci

FROM node:22-slim AS builder
WORKDIR /srv/overtake
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /srv/overtake/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* values are inlined into the bundle at build time, so the public
# site URL has to arrive here as a build argument. It is not a secret; it is the
# canonical origin used by metadataBase, robots.txt and the sitemap. Get it
# wrong and every canonical URL and OG tag points at the wrong host.
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL

# API_INTERNAL_URL must be a build argument too, which is not obvious. Next
# evaluates rewrites() while building and bakes the resolved destination into
# the standalone server, so a runtime environment variable never reaches it —
# the proxy silently keeps the localhost default and every /api/v1 call fails
# with ECONNREFUSED.
ARG API_INTERNAL_URL
ENV API_INTERNAL_URL=$API_INTERNAL_URL

RUN npm run build

# NOT /app. This application has a route named /app, and with the project
# rooted at /app the standalone server resolves every page through that
# segment — so every page inherits the signed-in-only layout and redirects to
# /signin. It only reproduces in the container, because locally the project
# never sits at /app.
FROM node:22-slim AS runner
WORKDIR /srv/overtake
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Never run as root.
RUN useradd --create-home --uid 10001 nextjs

# The standalone output ships its own minimal server; static assets and public/
# are not included in it and must be copied alongside.
COPY --from=builder /srv/overtake/public ./public
COPY --from=builder --chown=nextjs:nextjs /srv/overtake/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /srv/overtake/.next/static ./.next/static

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
