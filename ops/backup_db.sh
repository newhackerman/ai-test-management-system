#!/bin/bash
# ai-test-management-system 数据库备份
#
# 用途：把 ai_test_db 整库（结构 + 数据）备份到 $HOME/backups/ai-test-db/，
#       供 ops/recover.sh 在虚拟机替换后重建库时恢复。home 目录随虚拟机
#       替换持久化，/var/lib/mysql 不持久——这就是备份存在的意义。
#
# 用法：
#   bash ops/backup_db.sh            # 手动备份一次
#   由 cron 每小时调用一次（见 ai-test-db-backup 任务）
#
# 备份文件：ai_test_db-YYYYMMDD-HHMMSS-t<表数>.sql.gz，保留最近 7 份，
#           更旧的自动删除。文件名里的表数供恢复时校验 schema 是否匹配。
#
# 凭据：数据库密码只在运行时从 backend/.env 读取，绝不硬编码、
#       不输出到日志。备份本身是 gzip 压缩的 SQL 文本，含全部数据，
#       放在 home 目录下，不提交到 git。

set -u
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$REPO_DIR/backend"
ENV_FILE="$BACKEND_DIR/.env"
BACKUP_DIR="${HOME:-/home/hatch}/backups/ai-test-db"
KEEP=7
LOG_FILE="/tmp/ai-test-backup.log"

log() {
    local line
    line="$(date '+%Y-%m-%d %H:%M:%S') $*"
    echo "$line" | tee -a "$LOG_FILE"
}

env_val() { # env_val KEY -> value (no output if missing)
    grep -E "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-
}

DB_NAME="$(env_val MYSQL_DATABASE)"
DB_USER="$(env_val MYSQL_USER)"
DB_PORT="$(env_val MYSQL_PORT)"
DB_NAME="${DB_NAME:-ai_test_db}"
DB_USER="${DB_USER:-ai_test_user}"
DB_PORT="${DB_PORT:-3306}"

main() {
    local db_pass
    db_pass="$(env_val MYSQL_PASSWORD)"
    if [ -z "$db_pass" ]; then
        log "backup FAILED: MYSQL_PASSWORD not found in backend/.env"
        exit 1
    fi
    if ! mysqladmin -u "$DB_USER" -h 127.0.0.1 -P "$DB_PORT" \
            --password="$db_pass" ping >/dev/null 2>&1; then
        log "backup FAILED: cannot connect to MySQL as $DB_USER (is mysqld up?)"
        exit 1
    fi
    local tables
    tables="$(MYSQL_PWD="$db_pass" mysql -u "$DB_USER" -h 127.0.0.1 \
        -P "$DB_PORT" -N -e \
        "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='$DB_NAME';" 2>/dev/null || echo 0)"
    if [ "${tables:-0}" -lt 100 ]; then
        log "backup FAILED: only $tables tables in $DB_NAME, refusing to back up a half-built database"
        exit 1
    fi
    mkdir -p "$BACKUP_DIR" || { log "backup FAILED: cannot create $BACKUP_DIR"; exit 1; }
    local stamp file
    stamp="$(date '+%Y%m%d-%H%M%S')"
    file="$BACKUP_DIR/ai_test_db-${stamp}-t${tables}.sql.gz"
    # --single-transaction: 一致性快照，不锁表；--routines/--triggers:
    #   备份存储过程与触发器（当前库里没有，也无害）。
    #   密码经环境变量传入，不出现在 argv 与日志里。
    if MYSQL_PWD="$db_pass" mysqldump --single-transaction --routines --triggers \
            -u "$DB_USER" -h 127.0.0.1 -P "$DB_PORT" "$DB_NAME" 2>/dev/null \
            | gzip > "$file"; then
        local size
        size="$(stat -c%s "$file" 2>/dev/null || echo 0)"
        log "backup OK: $file (${size} bytes, $tables tables)"
    else
        rm -f "$file"
        log "backup FAILED: mysqldump failed"
        exit 1
    fi
    # 轮换：只留最近 KEEP 份。
    local old
    old="$(ls -1t "$BACKUP_DIR"/ai_test_db-*.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)))"
    if [ -n "$old" ]; then
        echo "$old" | xargs -r rm -f
        log "rotated old backups, kept latest $KEEP"
    fi
    unset db_pass
    exit 0
}

main "$@"
