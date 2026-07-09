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

# Stage 3: Serve with docusaurus serve (development mode with live docs).
FROM dependencies AS serve
# Create empty docs directory for mount point
RUN mkdir -p ./docs
EXPOSE 8080
# Use development mode which watches for changes
CMD ["npm", "run", "start", "--", "--host", "0.0.0.0", "--port", "8080"]

# Health check disabled temporarily due to Docusaurus config issue
# HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
#     CMD wget -q --spider http://localhost:8080 || exit 1
