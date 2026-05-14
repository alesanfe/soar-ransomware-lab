FROM nginx:1.25-alpine

# Copy static files
COPY index.html styles.css script.js /usr/share/nginx/html/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create health check endpoint
RUN echo 'location /health { access_log off; return 200 "healthy\n"; add_header Content-Type text/plain; }' > /etc/nginx/conf.d/health.conf

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -q --spider http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
