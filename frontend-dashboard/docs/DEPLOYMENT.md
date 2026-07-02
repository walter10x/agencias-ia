# Deployment

## Producción

### Build

```bash
npm run build
```

Genera los archivos estáticos en `dist/`. El build produce chunks optimizados (~11 archivos) con prefetching automático de Vite.

### Servir con Nginx

```nginx
server {
    listen 80;
    server_name dashboard.tudominio.com;
    root /var/www/frontend-dashboard/dist;
    index index.html;

    # SPA fallback — todas las rutas al index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy al backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /webhook/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Cache de assets estáticos
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Docker

```dockerfile
# Dockerfile
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

```yaml
# docker-compose.yml
version: "3.8"
services:
  frontend:
    build: .
    ports:
      - "80:80"
    depends_on:
      - backend

  backend:
    image: backend-agencias-ia
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
```

## Desarrollo

```bash
npm run dev
# Frontend en http://localhost:5173
# API proxy a http://localhost:8000
```

### Proxy (vite.config.ts)

| Ruta | Destino |
|------|---------|
| `/api/*` | `http://localhost:8000` |
| `/webhook/*` | `http://localhost:8000` |

## Variables de Entorno

No hay variables de entorno runtime — la configuración está hardcodeada en `vite.config.ts`. Si se necesita apuntar a otro backend, modificar el `target` del proxy.

## Preview

```bash
npm run preview
# Sirve el build de producción localmente para verificar
```
