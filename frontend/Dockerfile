# Multi-stage Dockerfile for AgriSys Frontend Web App & PWA
# Stage 1: Build production bundle with Node.js
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependency specifications
COPY package*.json ./
RUN npm install

# Copy source files and build
COPY . .
RUN npm run build

# Stage 2: Serve production assets with Nginx Alpine
FROM nginx:1.25-alpine

# Copy built assets to Nginx web root
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom reverse proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
