# syntax=docker/dockerfile:1
#
# DOCS-001/002: production build — `docusaurus build` at image-build time,
# static HTML served by nginx. No dev server, no webpack at runtime, no
# Node.js in the final image.

# Stage 1: reproducible dependencies (DOCS-008: npm ci, lockfile-pinned).
FROM node:22-alpine AS deps
WORKDIR /opt/docusaurus
COPY apps/docs-site/package.json apps/docs-site/package-lock.json ./
RUN npm ci

# Stage 2: static site build.
FROM deps AS build
COPY apps/docs-site/docusaurus.config.js apps/docs-site/sidebars.js ./
COPY apps/docs-site/src ./src
COPY apps/docs-site/static ./static
# Documentation tree: repo docs/ is the live source of truth.
COPY docs ./docs
# Generated reports referenced by the navbar (they live under reports/).
COPY reports/quality/quality-summary.md ./docs/reports/quality/quality-summary.md
COPY reports/test-review/test_review_report.md ./docs/reports/test-review/test_review_report.md
COPY reports/holistic/holistic_review_report.md ./docs/reports/holistic/holistic_review_report.md
COPY reports/e2e/e2e_report.md ./docs/reports/e2e/e2e_report.md
COPY reports/e2e/charts ./docs/reports/e2e/charts
RUN npm run build

# Stage 3: static serving — nginx only, non-root capable, read-only FS safe.
FROM nginx:1.27-alpine
COPY apps/docs-site/nginx.conf /etc/nginx/conf.d/default.conf
# baseUrl=/soar-ransomware-lab/ — the site must live under that path on
# disk or every asset/link 404s (and try_files loops to a 500).
COPY --from=build /opt/docusaurus/build /usr/share/nginx/html/soar-ransomware-lab
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget -q --spider http://localhost:8080/soar-ransomware-lab/ || exit 1
