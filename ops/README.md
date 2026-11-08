# ops — 环境恢复与开机自启

本目录是 AI 测试管理系统本地部署的运维脚本。应用代码与测试框架
不受影响（`qa-automation/` 之外没有改任何应用代码）。

## 背景

虚拟机替换后会丢的东西（非持久）：

- `/usr` 下 apt 装的 MySQL/Redis 二进制、`/var/lib/mysql` 数据、
  以及所有正在跑的服务进程。
- 不会丢的：`~/workspace`（仓库、`.env`、venv、node_modules 均持久）。

## 文件

| 文件 | 用途 |
| --- | --- |
| `recover.sh` | 幂等恢复脚本：逐个检查并补齐缺失的环节 |
| `rebuild_db.py` | 建表（保留外键约束，125 张表）+ 种子数据，供 `recover.sh` 调用 |
| `backup_db.sh` | 整库备份到 `~/backups/ai-test-db/`（每小时定时任务调用，保留最近 7 份）；`recover.sh` 重建库后自动从最新备份恢复数据 |
| `cleanup_soft_deleted.py` | 物理清理软删除残留行与孤儿文件（默认 dry-run，只看不删） |
| `verify_clean_install.sh` | 干净环境验证：全新 venv 里 `pip install -r requirements.txt` 并导入检查 |
| `systemd/*.service` | 后端/前端的 systemd 单元（进程内自启），由 `recover.sh` 负责链接与启用 |
| `README.md` | 本文件 |

## 恢复脚本的工作方式

`bash ops/recover.sh` 按顺序检查：

1. **apt 包**：`mysqld` / `redis-server` 缺失则重装（先用本地
   `/var/cache/apt/archives` 缓存免下载安装，再不行才 `apt-get update`
   后安装；apt 锁被占时最多等 5 分钟）。
2. **MySQL 进程**：没跑则启动（先试 `systemctl start mysql`，
   失败则直接 `mysqld --daemonize`；数据目录缺失则先
   `mysqld --initialize-insecure`）。包处于已解包未配置（iU）状态时
   先用缓存的 `.deb` 补装，`dpkg` 认得出缺失的系统用户并补建。
3. **空闲事务清理**：MySQL 起好后、建库前，只清理后端数据库用户
   的超时空闲事务（`COMMAND='Sleep'`、超过 60 秒且持有未提交事务），
   绝不碰 root 与系统线程；每条清理都记日志。这是兜底：事务泄漏
   的源头（两个进程级单例会话）已在后端修掉，见下。
3. **库与用户**：库 `ai_test_db`、用户 `ai_test_user` 缺失则重建，
   密码运行时从 `backend/.env` 读取。
4. **表与种子**：表少于 100 张或 admin 用户缺失则跑 `rebuild_db.py`
  （保留外键约束建表 + 权限/角色/admin 种子，幂等；半建成的库会
  先自检再重建，不会卡在“表已存在”上）。
5. **Redis 进程**：`redis-cli ping` 不通则拉起——先走 systemd 单元
  （`redis-server.service` 带 `PrivateUsers=false` 的 drop-in，
  之前 217/USER 起不来的问题已修），单元不可用时回退到
  `redis-server --daemonize yes` 直接启动。
6. **systemd 单元**：把 `systemd/*.service` 链接到
   `/etc/systemd/system/` 并 enable（进程内 `Restart=always`）。
7. **后端/前端**：健康检查不通则重启——单元已启用时走
   `systemctl restart ai-test-backend/frontend`（systemd 负责拉起，
   5 秒内自愈）；单元不可用时回退到 nohup 拉起。

全部正常时只做检查，什么都不动。日志在 `/tmp/ai-test-recover.log`，
退出码 0 表示最终全部健康，1 表示仍有未恢复的项（日志里有
`RECOVER FAILED` 行）。

凭据说明：脚本从不硬编码密码、不输出密码；数据库密码只在运行时
从 `backend/.env` 读，并通过 stdin/环境变量传给 mysql 客户端，
不会出现在进程参数里。

## 开机自启是怎么实现的

systemd 单元只负责**同一台虚拟机内**进程挂了重拉（`Restart=always`），
跨虚拟机替换靠运行时的 **cron 看护任务**：每 10 分钟运行一次
`bash ops/recover.sh`，替换后 10 分钟内自动把环境恢复起来。
cron 由平台管理，能跨虚拟机替换存活。

手动触发一次恢复：

```bash
bash ~/workspace/ai-test-management-system/ops/recover.sh
```

查看最近一次看护结果：

```bash
tail -20 /tmp/ai-test-recover.log
```

## 另外两个脚本

```bash
# 物理清理软删除残留（默认只看不删，加 --apply 才真删）
python3 ops/cleanup_soft_deleted.py            # dry-run，看会删多少
python3 ops/cleanup_soft_deleted.py --apply    # 真删（含孤儿文件）

# 干净环境依赖验证（全新 venv，装 requirements.txt 并导入检查）
bash ops/verify_clean_install.sh
```

清理脚本首跑删过 1666 行软删残留 + 50 个孤儿文件（21MB），再跑
就是 nothing to purge。两个脚本都不碰应用代码。

## 数据库备份与恢复（2026-11-07 新增）

虚拟机替换会清空 `/var/lib/mysql`，`recover.sh` 只能重建出种子
数据，库里的业务数据会丢。备份解决这个问题：

- `backup_db.sh`：`mysqldump --single-transaction` 整库备份到
  `~/backups/ai-test-db/`（home 目录随替换持久化），文件名带表数
  （`ai_test_db-YYYYMMDD-HHMMSS-t<表数>.sql.gz`），保留最近 7 份；
  每小时由定时任务 `ai-test-db-backup` 调用，失败才汇报。
- `recover.sh` 重建库成功后，自动从最新备份恢复：文件名里的表数
  须与刚重建的库一致（否则是旧 schema 的备份，跳过）；恢复失败
  不影响本次恢复结果（库里仍是刚建好的种子数据），只记日志。

手动备份 / 恢复：

```bash
bash ops/backup_db.sh        # 手动备份一次
ls -1t ~/backups/ai-test-db/ # 看最新备份
```

## 事务泄漏是怎么修的

后端曾有两个进程级单例会话（统计服务与会议 AI 服务的工厂函数）
建好后永不提交、回滚或关闭，启动预热一读就挂起一个事务直到进程
结束，看护重建库时会被表锁卡住几分钟。第六轮已把两个工厂改成
每次调用开短会话、用完回滚关闭（`INNODB_TRX` 归零，重建约 0.6 秒）。
`recover.sh` 里的空闲事务清理只是兜底，源头已不在。

## 已验证 / 未验证

- 已验证：kill 掉 MySQL、Redis、后端、前端四个服务后跑
  `recover.sh`，四个服务全部恢复且健康检查 200（跑过三轮：
  nohup 路径、修复 flock 泄漏后、单元路径）。
- 已验证：单元自愈——kill 掉单元管理的 uvicorn 后，systemd 在
  5 秒内拉起新进程，约 20 秒启动完成后健康检查恢复 200。
- 已验证：脚本退出干净——无残留 `recover.sh` 进程、无 flock
  占用；全部正常时立即复跑返回 `RECOVER OK`（约 1 秒）。
- 已验证：恢复脚本的修复历史——本次会话中已用它从“二进制丢失、
  数据目录清空、库/用户丢失”的状态完整重建过一次（apt 缓存
  安装 → 建库建用户 → 120 张表 + 45 权限/9 角色/1 admin 种子 →
  API 全量 275/275 + E2E 23/23 通过）。
- 未验证：**完整虚拟机替换**无法主动模拟；替换后首次恢复依赖
  cron 在 10 分钟内触发、`apt` 缓存里有 MySQL/Redis 的 `.deb`
  （当前缓存有 8.0.46/7.0.15 的完整闭包），以及平台 apt 索引
  可用。若缓存被清空且网络不可用，恢复会失败并在日志里留
  `RECOVER FAILED`。
