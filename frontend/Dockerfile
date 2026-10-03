FROM oven/bun:1-slim AS builder
WORKDIR /app

COPY package.json bun.lock* ./
RUN bun install

COPY . .
RUN bun run build

FROM oven/bun:1-slim
WORKDIR /app
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
ENV NODE_ENV=production
ENV PORT=3000

CMD ["bun", "./build/index.js"]
