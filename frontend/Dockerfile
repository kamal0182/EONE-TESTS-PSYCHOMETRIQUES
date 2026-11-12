FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# Modèle : au démarrage, ${NGINX_LOCAL_RESOLVERS} est remplacé par le DNS du
# conteneur (Docker : 127.0.0.11, Podman : passerelle du réseau).
ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
