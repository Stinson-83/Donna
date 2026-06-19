# Static build + serve for the Donna web dashboard (its own Railway service).
# Requires the donna-web service's Root Directory set to /webapp (so this is the
# build context). The VITE_* values are baked in at build time so the bundle
# points at the live API regardless of which .env files reach the build context.
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ENV VITE_MOCK=0
ENV VITE_API_BASE=https://donna-ai.up.railway.app
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/dist ./dist
ENV PORT=8080
EXPOSE 8080
# -s = SPA fallback (serve index.html for any path); the magic-link #t= fragment
# is client-side and never reaches the server.
CMD ["sh", "-c", "serve -s dist -l ${PORT:-8080}"]
