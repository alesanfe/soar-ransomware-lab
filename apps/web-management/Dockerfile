# WEB-EVAL-007: align with docs-site (nginx:1.27-alpine) — same static
# profile, one version to track for CVE bumps via Dependabot.
FROM nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10

# Copy static files
COPY index.html styles.css /usr/share/nginx/html/
COPY js/ /usr/share/nginx/html/js/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
