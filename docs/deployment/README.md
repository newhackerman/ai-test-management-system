# 部署指南

## 主推方式：Docker Compose（单机）

**`./deploy.sh` + `backend/docker-compose.yml`** 是主推部署方式：一台机器上
跑起前端、后端、MySQL、Redis 四个服务（另有生产档 nginx、开发档
phpMyAdmin / redis-commander 可选）。

```bash
# 先准备环境文件（模板见 backend/.env.example）
cp backend/.env.example backend/.env   # 填好数据库、Redis、JWT、AI 密钥
./deploy.sh dev          # 开发环境
./deploy.sh test         # 测试环境（需 backend/.env.test）
./deploy.sh prod         # 生产环境（需 backend/.env.production，会先备份数据库并要求确认）
./deploy.sh prod -f --no-backup   # 跳过确认与备份
./deploy.sh test --restart        # 仅重启服务
./deploy.sh --logs                # 跟随服务日志
```

流程：检查依赖与环境变量 → 建目录 →（prod 先备份）→ 构建镜像 →
`docker compose up -d` → 跑迁移（`backend/scripts/migrate_production.py`）
→ 健康检查（`http://localhost:8000/health`）。Compose v2（`docker compose`）
优先，缺失时回退 v1 `docker-compose`；compose 文件在 `backend/` 下，
脚本里写死了 `-f backend/docker-compose.yml`（仓库根目录没有 compose 文件）。

默认端口：前端 3000、后端 8000、MySQL 3306、Redis 6379；可用
`FRONTEND_PORT` / `BACKEND_PORT` / `MYSQL_PORT` / `REDIS_PORT` 等环境变量改。

### 直接用 Compose（不用 deploy.sh）

```bash
cd backend
docker compose up -d                    # 全部服务
docker compose --profile production up -d   # 另加 nginx 反向代理（见下）
docker compose --profile development up -d  # 另加 phpMyAdmin :8080、redis-commander :8081
```

## 其他方式

本地开发环境的自愈（测试虚拟机在用）：`ops/recover.sh` 每 10 分钟
由看护任务跑一次，服务挂了自动拉起、库丢了自动重建；还带空闲事务
兜底清理、软删物理清理与干净安装验证三个脚本。细节见
[`ops/README.md`](../../ops/README.md)。

| 方式 | 场景 | 说明 |
| --- | --- | --- |
| `scripts/deploy.sh <env> [version]` | 单机、想拉取已构建镜像而不是本地构建 | 同样走 `backend/docker-compose.yml`（脚本内先 `cd backend`）；用 `--env-file .env.<env>`；`production` 用 production profile。 |
| `scripts/k8s-deploy.sh [production\|staging]` + `k8s/*.yaml` | Kubernetes 集群 | 平铺 manifest：namespace、configmap、secrets、mysql、redis、backend、frontend、ingress。镜像占位 `ghcr.io/your-org/...`、secrets 里的 base64 值全是占位符，部署前必须替换。CI 的 build-and-push 会把镜像推到 ghcr.io（main 分支），但不负责 kubectl apply。 |
| `start_backend.sh` / `start_frontend.sh` | 本地开发（无 Docker） | venv + `pip install -r requirements.txt`，再起 uvicorn / Vite。当前测试虚拟机用的就是这条路（systemd 单元 + `ops/recover.sh` 自愈，见 `ops/`）。 |

## 不用的两套

- **`k8s/production/` 与 `k8s/staging/`**：环境分拆模板，但文件是 Go 模板风格
  （`replicas: {{REPLICAS}}`、`image: ...:{{IMAGE_TAG}}`），直接 `kubectl apply`
  会报 YAML 解析错；仓库里没有任何脚本做占位替换。想用 k8s 就用上面平铺的那套，
  这两个目录留待有人接手模板化时再处理。
- **`backend/requirements_async.txt`**：pin 的旧版依赖快照（FastAPI 0.104.1 等），
  CI 与部署都只用 `backend/requirements.txt`；留着是历史记录，不要拿它装环境。

## 已知缺口（修之前先知道）

- **本机未验证 `docker compose up`**：这台虚拟机没有安装 Docker，只能做到
  `bash -n` 语法检查 + YAML 解析 + 路径核对；首次在有 Docker 的机器上跑之前，
  先跑 `docker compose -f backend/docker-compose.yml config` 检查一遍。
- **nginx profile 缺文件**：`--profile production` 会挂载 `backend/nginx/nginx.conf`
  等文件，但 `backend/nginx/` 目录不存在，生产档目前起不来；需要时按
  `frontend:80` + `backend:8000` 的反代补一份 nginx 配置。
- **缺环境文件**：`backend/.env.test`、`backend/.env.production` 都不存在，
  跑 test/prod 前必须先创建（dev 用 `backend/.env`）。
- **迁移只覆盖 45 张表**：`alembic upgrade head` 只建迁移链里的 45 张表，
  其余表由后端启动时的 `create_all` 补齐；`scripts/deploy.sh` 的迁移步骤用的
  就是 alembic，跑完后以前端/后端健康检查为准，不要只看迁移退出码。
- **`k8s/secrets.yaml` 全是占位值**：`SECRET_KEY` 等写明了 CHANGE_THIS，
  上生产前必须替换成真实值（不要把真实值提交进仓库）。
