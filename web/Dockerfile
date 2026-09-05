# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# The Overtake web app. Built from web/ as the context, so this Dockerfile and
# web/fly.toml sit together and neither has to reach outside its own directory.
# ---------------------------------------------------------------------------

# Node 20 went end-of-life in April 2026; 22 is the supported LTS and satisfies
# the ">=20" engines constraint in package.json.
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
# `npm ci` rather than `npm install`: the lockfile is the build input, and a
# deploy must never silently resolve a different dependency tree than CI tested.
RUN npm ci

FROM node:22-slim AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* values are inlined into the bundle at build time, so the public
# site URL has to arrive here as a build argument. It is not a secret; it is the
# canonical origin used by metadataBase, robots.txt and the sitemap. Get it
# wrong and every canonical URL and OG tag points at the wrong host.
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
RUN npm run build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Never run as root.
RUN useradd --create-home --uid 10001 nextjs

# The standalone output ships its own minimal server; static assets and public/
# are not included in it and must be copied alongside.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

# API_INTERNAL_URL is read when the server boots (next.config.ts builds the
# rewrite from it), so it is supplied at runtime as a Fly secret rather than
# baked into the image.
CMD ["node", "server.js"]
