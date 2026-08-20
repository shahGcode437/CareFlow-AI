FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

# Vite bakes VITE_* variables into the JS bundle AT BUILD TIME (static
# replacement) — there is no way to change the API base URL at
# container-run time for a static nginx image. Defaults to exactly
# the value the app's own fallback already used
# (frontend/src/lib/apiClient.ts), so `docker build` with no args
# behaves identically to before. Override for a different deployment
# topology with:
#   docker build --build-arg VITE_API_BASE_URL=http://api.example.com .
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]