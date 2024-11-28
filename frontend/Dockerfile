# Etap 1: Budowanie aplikacji
FROM node:18-alpine AS build

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

# Etap 2: Uruchamianie aplikacji
FROM node:18-alpine

WORKDIR /app

COPY --from=build /app/package*.json ./
COPY --from=build /app/package-lock.json ./
COPY --from=build /app/next.config.js ./

RUN npm install --omit=dev

COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public

EXPOSE 80

CMD ["npm", "start"]
