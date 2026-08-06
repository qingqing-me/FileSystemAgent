# 构建阶段
FROM node:20-alpine AS build

WORKDIR /app

# 先拷贝依赖清单，利用 Docker 缓存
COPY package*.json ./
RUN npm install

# 拷贝源码并构建
COPY . .
RUN npm run build

# 运行阶段：nginx 托管静态文件
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
