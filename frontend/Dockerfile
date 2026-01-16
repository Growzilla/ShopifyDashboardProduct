# EcomDash V2 Frontend Dockerfile

# Development stage
FROM node:20-slim AS development

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Expose port
EXPOSE 3000

# Development server
CMD ["npm", "run", "dev"]

# Build stage
FROM node:20-slim AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM node:20-slim AS production

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY --from=build /app/build ./build

# Render.com injects PORT env var at runtime - DO NOT hardcode
# react-router-serve reads PORT from environment
EXPOSE 10000

CMD ["npm", "run", "start"]
