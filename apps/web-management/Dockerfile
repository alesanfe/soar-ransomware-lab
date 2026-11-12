# WEB-EVAL-007: align with docs-site (nginx:1.27-alpine) — same static
# profile, one version to track for CVE bumps via Dependabot.
FROM nginx:1.31-alpine@sha256:713fc2ebfd92e8217db451477182ee91944b123d2b1ee9fd5a8c6e91ca6c3a11

# Copy static files
COPY index.html styles.css /usr/share/nginx/html/
COPY js/ /usr/share/nginx/html/js/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
