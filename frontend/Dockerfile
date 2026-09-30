FROM node:alpine as build-stage

ENV TZ=Asia/Ho_Chi_Minh

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ARG REACT_APP_API_HOST

ENV REACT_APP_API_HOST=$REACT_APP_API_HOST

# Stage 1: build distribution files.
WORKDIR /dist
COPY . .
COPY package-lock.json .
RUN npm install
RUN npm run build

# Stage 2: build the image
FROM node:alpine
WORKDIR /app
COPY --from=build-stage /dist/build /app
RUN npm install -g serve
EXPOSE 3000
CMD ["serve", "-s", "."]