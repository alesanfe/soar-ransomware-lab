# syntax=docker/dockerfile:1

# Stage 1: Base image.
FROM node:lts-alpine AS base
WORKDIR /opt/docusaurus
ENV FORCE_COLOR=0

# Stage 2: Dependencies and config.
FROM base AS dependencies
WORKDIR /opt/docusaurus
COPY apps/docs-site/package*.json ./
RUN npm install
COPY apps/docs-site/docusaurus.config.js apps/docs-site/sidebars.js ./
COPY apps/docs-site/src ./src
COPY apps/docs-site/static ./static

# Stage 3: Serve with docusaurus serve (development mode with live docs).
FROM dependencies AS serve

# Copy the entrypoint script
COPY apps/docs-site/docker-entrypoint.sh /opt/docker-entrypoint.sh
RUN chmod +x /opt/docker-entrypoint.sh

# Copy chart images from reports/ into the image (will be synced at startup)
COPY reports/e2e/charts /opt/charts

# Copy operations images from docs/assets/images/ into the image
COPY docs/assets/images /opt/ops-images

# Copy the apps/docs-site/docs directory (includes reports/ markdown + _category_.json)
# This is baked into the image; the compose volume mount overrides docs/ at runtime,
# but the entrypoint syncs charts and creates placeholders as needed.
COPY apps/docs-site/docs /opt/docs-baked

# Create empty docs directory for the volume mount point
RUN mkdir -p ./docs

EXPOSE 8080

# Use the entrypoint to sync charts/placeholders, then start Docusaurus
ENTRYPOINT ["/opt/docker-entrypoint.sh"]
CMD ["npm", "run", "start", "--", "--host", "0.0.0.0", "--port", "8080"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget -q --spider http://localhost:8080 || exit 1
