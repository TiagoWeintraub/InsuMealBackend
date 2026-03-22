#!/usr/bin/env bash
# Push de la imagen InsuMeal backend a Docker Hub.
#
# Requisitos: docker login (una vez) con tu usuario de Docker Hub.
#
# Variables de entorno:
#   DOCKERHUB_USER  (obligatorio) tu usuario de Docker Hub
#   IMAGE_NAME      (opcional) nombre del repositorio en Hub; por defecto: insumeal-backend
#
# Uso:
#   export DOCKERHUB_USER=tu_usuario
#   ./docker-push.sh              # tag: latest
#   ./docker-push.sh v1.0.0       # tag explícito
#   IMAGE_NAME=insumeal ./docker-push.sh 1.2.3

set -euo pipefail

TAG="${1:-latest}"
DOCKERHUB_USER="${DOCKERHUB_USER:-}"
IMAGE_NAME="${IMAGE_NAME:-insumeal-backend}"

if [[ -z "$DOCKERHUB_USER" ]]; then
  echo "Error: definí DOCKERHUB_USER con tu usuario de Docker Hub." >&2
  echo "  export DOCKERHUB_USER=tu_usuario" >&2
  echo "  $0 [tag]" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

FULL_IMAGE="${DOCKERHUB_USER}/${IMAGE_NAME}:${TAG}"

echo "Building ${FULL_IMAGE} ..."
docker build -t "${FULL_IMAGE}" .

echo "Pushing ${FULL_IMAGE} ..."
docker push "${FULL_IMAGE}"

echo "Listo: ${FULL_IMAGE}"



# COMANDO PARA EJECUTARLO LOCAL
# docker build -t insumeal-backend:latest .