########################
#   Build  front-end   #
########################
FROM node:20-bullseye AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build          # ➜  /app/dist

########################
#   Serve with nginx   #
########################
FROM nginx:1.27-alpine
# 把编译好的静态文件放进 nginx 根目录
COPY --from=builder /app/dist /usr/share/nginx/html
# 把你刚才那份 server 块直接覆盖默认配置
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx","-g","daemon off;"]

