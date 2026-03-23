#!/usr/bin/env bash
# Push de la imagen InsuMeal Admin a Docker Hub.
#
# Requisitos: docker login (una vez) con tu usuario de Docker Hub.
#
# Variables de entorno:
#   DOCKERHUB_USER      (obligatorio) tu usuario de Docker Hub
#   IMAGE_NAME          (opcional) por defecto: insumeal-admin
#   VITE_API_BASE_URL   (opcional) URL pública del backend para build de Vite
#   PLATFORM            (opcional) por defecto: linux/amd64
#
# Uso:
#   export DOCKERHUB_USER=tiagoweintraun
#   ./docker-push.sh                  # tag: latest
#   ./docker-push.sh v1.0.0           # tag explícito
#   VITE_API_BASE_URL=https://api.tu-dominio.com ./docker-push.sh latest

set -euo pipefail

TAG="${1:-latest}"
DOCKERHUB_USER="${DOCKERHUB_USER:-}"
IMAGE_NAME="${IMAGE_NAME:-insumeal-admin}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://127.0.0.1:8000}"
PLATFORM="${PLATFORM:-linux/amd64}"

if [[ -z "$DOCKERHUB_USER" ]]; then
  echo "Error: definí DOCKERHUB_USER con tu usuario de Docker Hub." >&2
  echo "  export DOCKERHUB_USER=tiagoweintraun" >&2
  echo "  $0 [tag]" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

FULL_IMAGE="${DOCKERHUB_USER}/${IMAGE_NAME}:${TAG}"

echo "Building and pushing ${FULL_IMAGE} for ${PLATFORM} ..."
docker buildx build \
  --platform "${PLATFORM}" \
  --build-arg "VITE_API_BASE_URL=${VITE_API_BASE_URL}" \
  -t "${FULL_IMAGE}" \
  --push \
  .

echo "Listo: ${FULL_IMAGE}"
