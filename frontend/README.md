1 Requisitos
- Tener instalado Node.js 20+ y npm.

2 Configurar variables de entorno
- Copiar `.env_example` a `.env` en `frontend/`.
- Ajustar `VITE_API_BASE_URL` con la URL del backend.

3 Instalar dependencias (desde `frontend/`)
- `npm install`

4 Levantar el frontend en desarrollo
- `npm run dev`
- Abrir la URL que muestra Vite (por defecto `http://localhost:5173`).

5 Build de producción
- `npm run build`
- El resultado queda en `frontend/dist`.
