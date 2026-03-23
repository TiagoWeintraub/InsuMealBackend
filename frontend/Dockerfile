# Imagen de producción para InsuMeal Admin (React + Vite + Nginx).
# Build:  docker build -t insumeal-admin:latest .
# Run:    docker run --rm -p 8080:80 insumeal-admin:latest
#
# Variables opcionales de build:
#   --build-arg VITE_API_BASE_URL=https://api.example.com

FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
