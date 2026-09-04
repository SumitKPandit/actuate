FROM node:22-alpine

WORKDIR /app/frontend

COPY package*.json ./
RUN npm ci

COPY . ./
ARG VITE_API_URL="http://127.0.0.1:8000"
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "preview", "--", "--port", "3000", "--host", "0.0.0.0"]
