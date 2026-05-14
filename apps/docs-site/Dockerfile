# syntax=docker/dockerfile:1

# Stage 1: Base image.
FROM node:lts-alpine AS base
WORKDIR /opt/docusaurus
ENV FORCE_COLOR=0

# Stage 2: Production build mode.
FROM base AS build
WORKDIR /opt/docusaurus
COPY apps/docs-site/package*.json ./
RUN npm install
COPY apps/docs-site/docusaurus.config.js apps/docs-site/sidebars.js ./
COPY apps/docs-site/src ./src
COPY docs ./docs
RUN npm run build

# Stage 3: Serve with docusaurus serve.
FROM build AS serve
EXPOSE 3000
CMD ["npm", "run", "serve", "--", "--host", "0.0.0.0", "--no-open"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -q --spider http://localhost:3000 || exit 1
