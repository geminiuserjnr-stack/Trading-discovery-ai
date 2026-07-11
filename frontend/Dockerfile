# Phase 1: Build static assets
FROM node:22-slim AS builder

WORKDIR /app

# Declare build-time arguments so Railway can inject them
ARG VITE_API_URL
ARG VITE_WS_URL

# Expose them as env variables for the Vite compiler
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

# Copy lock files and packages
COPY package.json package-lock.json* ./

# Install packages with legacy peer deps to handle Recharts react 19 compatibility
RUN npm ci --legacy-peer-deps || npm install --legacy-peer-deps

# Copy source files
COPY . .

# Run build
RUN npm run build

# Phase 2: Serve securely via Nginx
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose Nginx default port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
