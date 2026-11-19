# WEB-EVAL-007: align with docs-site (nginx:1.27-alpine) — same static
# profile, one version to track for CVE bumps via Dependabot.
FROM nginx:1.29-alpine@sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de

# Copy static files
COPY index.html styles.css /usr/share/nginx/html/
COPY js/ /usr/share/nginx/html/js/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
