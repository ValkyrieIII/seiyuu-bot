# ---- 构建阶段：pnpm 安装依赖并产出静态产物 ----
FROM node:22-alpine AS build
WORKDIR /app

# 启用 corepack 并使用与 lockfile(9.0) 兼容的 pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# 先拷贝依赖清单，利用 Docker 层缓存
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# 拷贝源码并构建（vue-tsc 类型检查 + vite build）
COPY . .
RUN pnpm build

# ---- 运行阶段：nginx 托管静态产物，/admin 反代到后端 ----
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
