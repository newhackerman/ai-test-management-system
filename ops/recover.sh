#!/bin/bash
# ai-test-management-system 一键恢复 / 看护脚本
#
# 用途：虚拟机替换（或服务意外停止）后，把本地部署恢复到可用状态。
# 幂等：全部正常时只做健康检查，不重启、不重建任何东西；缺什么补什么。
#
# 用法：
#   bash ops/recover.sh            # 手动恢复 / 健康检查
#   由运行时 cron 每 10 分钟调用一次（见 ops/README.md）
#
# 恢复顺序：apt 包（MySQL/Redis 二进制）-> MySQL 进程 -> 库/用户 ->
#           表结构+种子 -> Redis 进程 -> 后端 -> 前端
#
# 凭据：数据库密码只在运行时从 backend/.env 读取，绝不硬编码、
#       不输出到日志。日志见 /tmp/ai-test-recover.log。

set -u
export PATH="/opt/hatch-image/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"
ENV_FILE="$BACKEND_DIR/.env"
LOG_FILE="/tmp/ai-test-recover.log"
LOCK_FILE="/tmp/ai-test-recover.lock"
SYSTEMD_DIR="$SCRIPT_DIR/systemd"

REPAIRED=()
FAILED=()

log() {
    local line
    line="$(date '+%Y-%m-%d %H:%M:%S') $*"
    echo "$line" | tee -a "$LOG_FILE"
}

repaired() { REPAIRED+=("$1"); log "REPAIRED: $1"; }
failed()   { FAILED+=("$1"); log "FAILED: $1"; }

# --- .env ---------------------------------------------------------------
env_val() { # env_val KEY -> value (no output if missing)
    grep -E "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-
}

DB_NAME="$(env_val MYSQL_DATABASE)"
DB_USER="$(env_val MYSQL_USER)"
DB_PORT="$(env_val MYSQL_PORT)"
DB_NAME="${DB_NAME:-ai_test_db}"
DB_USER="${DB_USER:-ai_test_user}"
DB_PORT="${DB_PORT:-3306}"

# --- apt ------------------------------------------------------------------
wait_apt_lock() { # wait up to 300s for the apt lists lock
    local i
    for i in $(seq 1 60); do
        if ! sudo fuser /var/lib/apt/lists/lock >/dev/null 2>&1; then
            return 0
        fi
        sleep 5
    done
    return 1
}

pkg_ok() { # pkg_ok PKG -> 0 iff dpkg status is "install ok installed"
    # 第 12 项：只查二进制存在会漏掉 iU（已解包未配置）状态——此时
    # mysqld/redis-server 二进制都在，但 mysql 用户、postinst 都没
    # 跑，服务起不来，redis 的 systemd 单元还会报 217/USER。
    local st
    st="$(dpkg-query -W -f='${Status}' "$1" 2>/dev/null || echo unknown)"
    [ "$st" = "install ok installed" ]
}

repair_broken_packages() {
    # 修 iU/iF/半配置状态：先 --fix-broken，再 dpkg --configure -a。
    log "repairing broken/unconfigured packages..."
    wait_apt_lock || log "apt lock wait timed out, proceeding anyway"
    sudo DEBIAN_FRONTEND=noninteractive apt-get --fix-broken install -y >/dev/null 2>&1 || true
    sudo dpkg --configure -a >/dev/null 2>&1 || true
}

ensure_packages() {
    local missing=() broken=()
    for pkg in mysql-server redis-server; do
        if ! pkg_ok "$pkg"; then
            if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -qE 'unpacked|half-configured|half-installed|triggers-awaited|reinstreq'; then
                broken+=("$pkg")
            else
                missing+=("$pkg")
            fi
        fi
    done
    [ "${#missing[@]}" -eq 0 ] && [ "${#broken[@]}" -eq 0 ] && return 0

    if [ "${#broken[@]}" -gt 0 ]; then
        log "unconfigured packages (iU/iF state), repairing: ${broken[*]}"
        repair_broken_packages
        # 重新评估：修好后从 missing 里去掉
        local still_missing=()
        for pkg in "${missing[@]}" "${broken[@]}"; do
            pkg_ok "$pkg" || still_missing+=("$pkg")
        done
        missing=("${still_missing[@]}")
        [ "${#missing[@]}" -eq 0 ] && { repaired "repaired unconfigured packages: ${broken[*]}"; return 0; }
    fi

    log "missing binaries, installing: ${missing[*]}"
    wait_apt_lock || log "apt lock wait timed out, proceeding anyway"
    # Cache first: the archive cache survives VM replacement, so a
    # reinstall usually needs no network at all.
    if sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-download "${missing[@]}" >/dev/null 2>&1; then
        :
    elif sudo DEBIAN_FRONTEND=noninteractive apt-get update >/dev/null 2>&1 \
        && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing[@]}" >/dev/null 2>&1; then
        :
    elif [ -d /var/cache/apt/archives ] \
        && sudo dpkg -i /var/cache/apt/archives/*.deb >/dev/null 2>&1; then
        :
    else
        failed "apt install ${missing[*]}"
        return 1
    fi
    if pkg_ok mysql-server && pkg_ok redis-server \
        && command -v mysqld >/dev/null 2>&1 && command -v redis-server >/dev/null 2>&1; then
        repaired "installed missing packages: ${missing[*]}"
        return 0
    fi
    failed "packages still not installed after install: ${missing[*]}"
    return 1
}

# --- MySQL ------------------------------------------------------------------
ensure_mysql_running() {
    if pgrep -x mysqld >/dev/null 2>&1; then
        return 0
    fi
    log "mysqld not running, starting..."
    if [ ! -d /var/lib/mysql/mysql ]; then
        log "mysql data dir missing/empty, initializing..."
        sudo mkdir -p /var/lib/mysql /var/run/mysqld
        sudo chown mysql:mysql /var/lib/mysql /var/run/mysqld 2>/dev/null || true
        sudo mysqld --initialize-insecure --user=mysql >/dev/null 2>&1 \
            || { failed "mysqld --initialize-insecure"; return 1; }
    fi
    if ! sudo systemctl start mysql >/dev/null 2>&1 \
        || ! sudo systemctl is-active --quiet mysql; then
        log "systemctl start mysql failed, starting mysqld directly..."
        sudo mysqld --daemonize --user=mysql 9>&- >/dev/null 2>&1
    fi
    local i
    for i in $(seq 1 30); do
        sudo mysqladmin -u root ping >/dev/null 2>&1 && break
        sleep 2
    done
    if pgrep -x mysqld >/dev/null 2>&1 \
        && sudo mysqladmin -u root ping >/dev/null 2>&1; then
        repaired "started mysqld"
        return 0
    fi
    failed "mysqld did not come up"
    return 1
}

ensure_mysql_db_user() {
    local db_pass
    db_pass="$(env_val MYSQL_PASSWORD)"
    if [ -z "$db_pass" ]; then
        failed "MYSQL_PASSWORD not found in backend/.env"
        return 1
    fi
    # Password is passed via stdin heredoc only; never echoed, never in argv.
    sudo mysql -u root <<SQL >/dev/null 2>&1
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'127.0.0.1' IDENTIFIED BY '$db_pass';
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$db_pass';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'127.0.0.1';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL
    unset db_pass
    if MYSQL_PWD="$(env_val MYSQL_PASSWORD)" mysql -u "$DB_USER" -h 127.0.0.1 \
            -P "$DB_PORT" -e "USE \`$DB_NAME\`;" >/dev/null 2>&1; then
        return 0
    fi
    failed "cannot connect as $DB_USER to $DB_NAME"
    return 1
}

ensure_tables() {
    local tables admin
    tables="$(MYSQL_PWD="$(env_val MYSQL_PASSWORD)" mysql -u "$DB_USER" -h 127.0.0.1 \
        -P "$DB_PORT" -N -e \
        "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='$DB_NAME';" 2>/dev/null || echo 0)"
    admin="$(MYSQL_PWD="$(env_val MYSQL_PASSWORD)" mysql -u "$DB_USER" -h 127.0.0.1 \
        -P "$DB_PORT" -N -e \
        "SELECT COUNT(*) FROM \`$DB_NAME\`.users WHERE username='admin';" 2>/dev/null || echo 0)"
    # 第 12 项：只看表数+admin 会漏掉“半种子库”（表全、admin 在，
    # 但权限/角色只种了一部分）。种子数是 PermissionService 里的
    # 固定种子规模：45 个权限、9 个角色。
    local perms roles
    perms="$(MYSQL_PWD="$(env_val MYSQL_PASSWORD)" mysql -u "$DB_USER" -h 127.0.0.1 \
        -P "$DB_PORT" -N -e \
        "SELECT COUNT(*) FROM \`$DB_NAME\`.permissions;" 2>/dev/null || echo 0)"
    roles="$(MYSQL_PWD="$(env_val MYSQL_PASSWORD)" mysql -u "$DB_USER" -h 127.0.0.1 \
        -P "$DB_PORT" -N -e \
        "SELECT COUNT(*) FROM \`$DB_NAME\`.roles;" 2>/dev/null || echo 0)"
    if [ "${tables:-0}" -ge 100 ] && [ "${admin:-0}" -ge 1 ] \
        && [ "${perms:-0}" -ge 45 ] && [ "${roles:-0}" -ge 9 ]; then
        return 0
    fi
    log "tables=$tables admin=$admin permissions=$perms roles=$roles, rebuilding database..."
    if "$BACKEND_DIR/venv/bin/python" "$SCRIPT_DIR/rebuild_db.py" >>"$LOG_FILE" 2>&1; then
        repaired "rebuilt database (tables + seed)"
        return 0
    fi
    failed "rebuild_db.py failed (see $LOG_FILE)"
    return 1
}

# --- Redis ------------------------------------------------------------------
ensure_redis_unit_override() {
    # 第 12 项：发行版 redis-server 单元含 PrivateUsers=true，在本机
    # VM 上建用户命名空间失败（217/USER），与 redis 用户是否存在无关。
    # 用 drop-in 只关掉 PrivateUsers，其余沙箱不动。/etc 不随虚拟机
    # 替换持久化，所以每次运行都检查安装（源文件在 ops/systemd 下）。
    local src="$SCRIPT_DIR/systemd/redis-server.service.d/override.conf"
    local dst="/etc/systemd/system/redis-server.service.d/override.conf"
    [ -f "$src" ] || return 0
    if [ ! -f "$dst" ] || ! cmp -s "$src" "$dst"; then
        sudo mkdir -p /etc/systemd/system/redis-server.service.d
        sudo cp "$src" "$dst" 2>/dev/null \
            && sudo systemctl daemon-reload >/dev/null 2>&1 \
            && log "installed redis-server unit override (PrivateUsers=false)"
    fi
}

ensure_redis() {
    if redis-cli ping 2>/dev/null | grep -qx PONG; then
        return 0
    fi
    log "redis not responding, starting redis-server..."
    # 第 12 项：先走发行版 systemd 单元（正常路径；PrivateUsers
    # 导致的 217/USER 由 ensure_redis_unit_override 的 drop-in 解决，
    # 仍失败则可能是包未配置、redis 用户缺失——修包再重试；单元再
    # 失败才退回直接拉起（旧行为），并在日志里写明。
    local i
    if sudo systemctl start redis-server >/dev/null 2>&1; then
        for i in $(seq 1 10); do
            redis-cli ping 2>/dev/null | grep -qx PONG && break
            sleep 1
        done
    fi
    if redis-cli ping 2>/dev/null | grep -qx PONG; then
        repaired "started redis-server (systemd unit)"
        return 0
    fi
    if ! id redis >/dev/null 2>&1; then
        log "redis user missing, package likely unconfigured; repairing..."
        repair_broken_packages
        if sudo systemctl start redis-server >/dev/null 2>&1; then
            for i in $(seq 1 10); do
                redis-cli ping 2>/dev/null | grep -qx PONG && break
                sleep 1
            done
        fi
        if redis-cli ping 2>/dev/null | grep -qx PONG; then
            repaired "started redis-server (systemd unit, after package repair)"
            return 0
        fi
    fi
    log "systemd unit failed, falling back to direct redis-server start"
    pkill -x redis-server 2>/dev/null || true
    redis-server --daemonize yes 9>&- >/dev/null 2>&1
    for i in $(seq 1 15); do
        redis-cli ping 2>/dev/null | grep -qx PONG && break
        sleep 1
    done
    if redis-cli ping 2>/dev/null | grep -qx PONG; then
        repaired "started redis-server (direct fallback; systemd unit still broken)"
        return 0
    fi
    failed "redis-server did not come up"
    return 1
}

# --- systemd units (backend/frontend, in-process restart) ------------------
ensure_systemd_units() {
    # Units live in ops/systemd/ (persistent); link + enable them so a
    # plain process crash restarts inside the VM. Cross-VM recovery does
    # NOT depend on this -- the cron + this script is the mechanism.
    [ -d "$SYSTEMD_DIR" ] || return 0
    local unit changed=0
    for unit in "$SYSTEMD_DIR"/*.service; do
        [ -f "$unit" ] || continue
        local name
        name="$(basename "$unit")"
        if [ ! -L "/etc/systemd/system/$name" ]; then
            sudo ln -sf "$unit" "/etc/systemd/system/$name" 2>/dev/null && changed=1
        fi
        if ! sudo systemctl is-enabled --quiet "$name" 2>/dev/null; then
            sudo systemctl enable "$name" >/dev/null 2>&1 && changed=1
        fi
    done
    [ "$changed" -eq 1 ] && sudo systemctl daemon-reload >/dev/null 2>&1
    return 0
}

# --- backend / frontend -------------------------------------------------------
health_ok() { # health_ok URL
    curl -fsS -m 5 -o /dev/null "$1" 2>/dev/null
}

ensure_backend() {
    if health_ok "http://localhost:8000/api/v1/health"; then
        return 0
    fi
    log "backend unhealthy, (re)starting..."
    if systemctl is-enabled --quiet ai-test-backend.service 2>/dev/null; then
        # Unit-managed: single owner (systemd restarts on crash).
        sudo systemctl restart ai-test-backend.service >/dev/null 2>&1
    else
        pkill -f "uvicorn src.main:app" 2>/dev/null || true
        sleep 1
        # setsid + disown: fully detach the daemon. A bare "( ... & )"
        # subshell waits for its background job, which left stray
        # recover.sh processes holding the flock and the caller's pipe.
        cd "$BACKEND_DIR"
        setsid nohup ./venv/bin/python -m uvicorn src.main:app \
            --host 0.0.0.0 --port 8000 >>/tmp/ai-backend.log 2>&1 < /dev/null 9>&- &
        disown
        cd "$REPO_DIR"
    fi
    local i
    for i in $(seq 1 30); do
        health_ok "http://localhost:8000/api/v1/health" && break
        sleep 2
    done
    if health_ok "http://localhost:8000/api/v1/health"; then
        repaired "started backend (uvicorn :8000)"
        return 0
    fi
    failed "backend health check failed after restart"
    return 1
}

ensure_frontend() {
    if health_ok "http://localhost:3000/"; then
        return 0
    fi
    log "frontend unhealthy, (re)starting..."
    if systemctl is-enabled --quiet ai-test-frontend.service 2>/dev/null; then
        sudo systemctl restart ai-test-frontend.service >/dev/null 2>&1
    else
        pkill -f "vite --port 3000" 2>/dev/null || true
        sleep 1
        cd "$FRONTEND_DIR"
        setsid nohup npm run dev -- --port 3000 --host 0.0.0.0 \
            >>/tmp/ai-frontend.log 2>&1 < /dev/null 9>&- &
        disown
        cd "$REPO_DIR"
    fi
    local i
    for i in $(seq 1 30); do
        health_ok "http://localhost:3000/" && break
        sleep 2
    done
    if health_ok "http://localhost:3000/"; then
        repaired "started frontend (vite :3000)"
        return 0
    fi
    failed "frontend health check failed after restart"
    return 1
}

# --- main ---------------------------------------------------------------------
main() {
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
        log "another recover run is active, skipping"
        exit 0
    fi
    : >>"$LOG_FILE"
    log "--- recover run start ---"

    ensure_packages
    if ! ensure_mysql_running; then
        log "mysql unavailable, skipping db/table checks"
    else
        ensure_mysql_db_user
        ensure_tables
    fi
    ensure_redis_unit_override
    ensure_redis
    ensure_systemd_units
    ensure_backend
    ensure_frontend

    if [ "${#FAILED[@]}" -gt 0 ]; then
        log "RECOVER FAILED: ${FAILED[*]}"
        exit 1
    fi
    if [ "${#REPAIRED[@]}" -gt 0 ]; then
        log "RECOVER REPAIRED: ${REPAIRED[*]}"
    else
        log "RECOVER OK: all services healthy"
    fi
    exit 0
}

main "$@"
