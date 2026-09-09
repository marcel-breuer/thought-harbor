FROM node:22-alpine AS dependencies

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@10.15.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile

FROM node:22-alpine AS builder

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@10.15.0 --activate

COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=dependencies /app/apps/web/node_modules ./apps/web/node_modules
COPY . .
RUN pnpm --dir apps/web build
RUN pnpm --filter @thoughtharbor/web deploy --prod --legacy /app/deploy

FROM node:22-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

COPY --from=builder /app/apps/web/build ./build
COPY --from=builder /app/deploy/node_modules ./node_modules

USER node

EXPOSE 3000

CMD ["node", "build"]
