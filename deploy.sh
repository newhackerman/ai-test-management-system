#!/bin/bash

# AI测试管理系统 - 自动化部署脚本
# 支持开发环境、测试环境和生产环境的自动化部署

set -e  # 遇到错误立即退出
set -o pipefail  # 管道命令中任何一个失败都退出

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="ai-test-management-system"
COMPOSE_PROJECT_NAME="ai_test_mgmt"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# 显示使用说明
show_usage() {
    cat << EOF
AI测试管理系统 - 自动化部署脚本

使用方法:
    $0 [选项] <环境>

参数:
    环境:
        dev         部署到开发环境
        test        部署到测试环境
        prod        部署到生产环境

选项:
    -h, --help      显示此帮助信息
    -v, --verbose   启用详细输出
    -f, --force     强制部署（跳过确认）
    --no-backup     跳过数据库备份
    --no-migrate    跳过数据库迁移
    --build-only    仅构建镜像，不启动服务
    --restart       重启现有服务
    --logs          显示服务日志

示例:
    $0 dev                      # 部署到开发环境
    $0 prod -v --no-backup      # 部署到生产环境（详细输出，不备份）
    $0 test --restart           # 重启测试环境服务

EOF
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    local missing_deps=()
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing_deps+=("docker-compose")
    fi
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "缺少依赖: ${missing_deps[*]}"
        log_error "请先安装所需依赖后再运行部署脚本"
        exit 1
    fi
    
    log_info "依赖检查完成"
}

# 检查环境变量
check_environment_variables() {
    local env=$1
    log_info "检查环境变量..."
    
    local env_file=""
    case $env in
        "dev")
            env_file="backend/.env"
            ;;
        "test")
            env_file="backend/.env.test"
            ;;
        "prod")
            env_file="backend/.env.production"
            ;;
    esac
    
    if [[ ! -f "$env_file" ]]; then
        log_error "环境配置文件不存在: $env_file"
        log_error "请先创建相应的环境配置文件"
        exit 1
    fi
    
    # 检查关键环境变量
    local required_vars=("DATABASE_URL" "JWT_SECRET_KEY" "REDIS_URL")
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$env_file"; then
            log_error "环境配置文件中缺少必需变量: $var"
            exit 1
        fi
    done
    
    log_info "环境变量检查完成"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    local dirs=(
        "logs"
        "uploads" 
        "backups"
        "data/mysql"
        "data/redis"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_debug "创建目录: $dir"
    done
    
    log_info "目录创建完成"
}

# 备份数据库
backup_database() {
    local env=$1
    
    if [[ "$SKIP_BACKUP" == "true" ]]; then
        log_info "跳过数据库备份"
        return 0
    fi
    
    log_info "创建数据库备份..."
    
    # 检查数据库服务是否运行
    if docker-compose -p "$COMPOSE_PROJECT_NAME" ps mysql | grep -q "Up"; then
        local backup_name="backup_$(date +%Y%m%d_%H%M%S).sql"
        docker-compose -p "$COMPOSE_PROJECT_NAME" exec -T mysql mysqldump \
            -u root -p"${MYSQL_ROOT_PASSWORD:-rootpassword}" \
            "${MYSQL_DATABASE:-ai_test_management}" > "backups/$backup_name"
        
        log_info "数据库备份完成: backups/$backup_name"
    else
        log_warn "数据库服务未运行，跳过备份"
    fi
}

# 构建镜像
build_images() {
    local env=$1
    log_info "构建Docker镜像..."
    
    # 设置构建参数
    local build_args=""
    if [[ "$env" == "prod" ]]; then
        build_args="--target production"
    fi
    
    # 构建后端镜像
    docker build $build_args -t "${PROJECT_NAME}-backend:$env" backend/
    
    # 构建前端镜像（如果存在Dockerfile）
    if [[ -f "frontend/Dockerfile" ]]; then
        docker build -t "${PROJECT_NAME}-frontend:$env" frontend/
    fi
    
    log_info "镜像构建完成"
}

# 运行数据库迁移
run_migrations() {
    local env=$1
    
    if [[ "$SKIP_MIGRATE" == "true" ]]; then
        log_info "跳过数据库迁移"
        return 0
    fi
    
    log_info "运行数据库迁移..."
    
    # 等待数据库服务启动
    log_info "等待数据库服务启动..."
    docker-compose -p "$COMPOSE_PROJECT_NAME" exec -T mysql bash -c '
        until mysqladmin ping -h localhost --silent; do
            echo "等待MySQL启动..."
            sleep 2
        done
    '
    
    # 运行迁移
    local env_file=""
    case $env in
        "dev") env_file="backend/.env" ;;
        "test") env_file="backend/.env.test" ;;
        "prod") env_file="backend/.env.production" ;;
    esac
    
    # 获取数据库连接信息
    local database_url=$(grep "^DATABASE_URL=" "$env_file" | cut -d'=' -f2- | tr -d '"')
    
    python3 backend/scripts/migrate_production.py \
        --database-url "$database_url" \
        ${FORCE_DEPLOY:+--force}
    
    log_info "数据库迁移完成"
}

# 启动服务
start_services() {
    local env=$1
    log_info "启动服务..."
    
    # 选择合适的compose文件
    local compose_file="docker-compose.yml"
    if [[ -f "docker-compose.$env.yml" ]]; then
        compose_file="docker-compose.$env.yml"
    fi
    
    # 设置环境变量
    export COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME"
    export ENVIRONMENT="$env"
    
    # 启动服务
    docker-compose -f "$compose_file" -p "$COMPOSE_PROJECT_NAME" up -d
    
    log_info "服务启动完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
            log_info "健康检查通过"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log_debug "健康检查失败，重试 ($attempt/$max_attempts)"
        sleep 10
    done
    
    log_error "健康检查失败，服务可能未正常启动"
    return 1
}

# 显示部署状态
show_status() {
    log_info "=== 部署状态 ==="
    docker-compose -p "$COMPOSE_PROJECT_NAME" ps
    
    log_info "=== 服务日志（最近20行）==="
    docker-compose -p "$COMPOSE_PROJECT_NAME" logs --tail=20
}

# 显示服务日志
show_logs() {
    log_info "显示服务日志..."
    docker-compose -p "$COMPOSE_PROJECT_NAME" logs -f
}

# 重启服务
restart_services() {
    log_info "重启服务..."
    docker-compose -p "$COMPOSE_PROJECT_NAME" restart
    log_info "服务重启完成"
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    docker-compose -p "$COMPOSE_PROJECT_NAME" down
    log_info "服务停止完成"
}

# 清理资源
cleanup() {
    log_info "清理未使用的Docker资源..."
    docker system prune -f
    docker volume prune -f
    log_info "清理完成"
}

# 主部署函数
deploy() {
    local env=$1
    
    log_info "开始部署到 $env 环境..."
    
    # 执行部署步骤
    check_dependencies
    check_environment_variables "$env"
    create_directories
    
    if [[ "$BUILD_ONLY" == "true" ]]; then
        build_images "$env"
        log_info "镜像构建完成，跳过服务启动"
        exit 0
    fi
    
    # 备份数据库（生产环境）
    if [[ "$env" == "prod" ]]; then
        backup_database "$env"
    fi
    
    # 构建和启动
    build_images "$env"
    start_services "$env"
    
    # 数据库迁移
    run_migrations "$env"
    
    # 健康检查
    if ! health_check; then
        log_error "部署失败：健康检查未通过"
        show_status
        exit 1
    fi
    
    show_status
    
    log_info "=== 部署完成 ==="
    log_info "前端访问地址: http://localhost:3000"
    log_info "后端API地址: http://localhost:8000"
    log_info "API文档地址: http://localhost:8000/docs"
    
    if [[ "$env" == "dev" ]]; then
        log_info "phpMyAdmin: http://localhost:8080"
    fi
}

# 解析命令行参数
ENVIRONMENT=""
VERBOSE=false
FORCE_DEPLOY=false
SKIP_BACKUP=false
SKIP_MIGRATE=false
BUILD_ONLY=false
RESTART_ONLY=false
SHOW_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            DEBUG=true
            shift
            ;;
        -f|--force)
            FORCE_DEPLOY=true
            shift
            ;;
        --no-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --no-migrate)
            SKIP_MIGRATE=true
            shift
            ;;
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --restart)
            RESTART_ONLY=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        dev|test|prod)
            ENVIRONMENT=$1
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_usage
            exit 1
            ;;
    esac
done

# 检查环境参数
if [[ -z "$ENVIRONMENT" ]] && [[ "$SHOW_LOGS" != "true" ]] && [[ "$RESTART_ONLY" != "true" ]]; then
    log_error "请指定部署环境: dev, test, 或 prod"
    show_usage
    exit 1
fi

# 执行相应操作
if [[ "$SHOW_LOGS" == "true" ]]; then
    show_logs
elif [[ "$RESTART_ONLY" == "true" ]]; then
    restart_services
else
    # 生产环境部署确认
    if [[ "$ENVIRONMENT" == "prod" ]] && [[ "$FORCE_DEPLOY" != "true" ]]; then
        echo
        log_warn "即将部署到生产环境！"
        log_warn "这将影响正在运行的服务。"
        echo
        read -p "确认继续部署到生产环境? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "部署已取消"
            exit 0
        fi
    fi
    
    deploy "$ENVIRONMENT"
fi