FROM node:22-bookworm-slim AS build

WORKDIR /app

COPY package.json ./
ARG NPM_REGISTRY=https://registry.npmjs.org/
RUN npm config set registry "${NPM_REGISTRY}" && npm install

COPY . .

# Empty = same-origin requests; nginx proxies API paths to the app service.
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 443
