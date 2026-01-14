# EcomDash V2 Frontend Dockerfile

# Development stage
FROM node:20-alpine as development

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
FROM node:20-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine as production

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY --from=build /app/build ./build

# Render.com injects PORT env var - react-router-serve respects it
ENV PORT=3000
EXPOSE 3000

CMD ["npm", "run", "start"]
