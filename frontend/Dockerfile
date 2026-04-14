FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine

# Create non-root user and set ownership of nginx directories
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -s /bin/sh -D appuser && \
    chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown appuser:appuser /var/run/nginx.pid

COPY --from=build --chown=appuser:appuser /app/dist /usr/share/nginx/html

# Use envsubst to templatize nginx config for configurable backend URL
ENV BACKEND_URL=backend:8000
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

USER appuser

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
