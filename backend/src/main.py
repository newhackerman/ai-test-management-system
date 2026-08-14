from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import logging
import traceback
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware

from .core.config import get_settings
from .core.database import init_database, close_database
from .core.service_registry import configure_services, initialize_application_services
from .core.fastapi_integration import setup_dependency_injection
from .middleware.performance_middleware import setup_performance_monitoring
from .utils.config_manager import get_config_manager
from .utils.jwt import jwt_service
from .api import api_router

# 获取配置管理器
config_manager = get_config_manager()

# 设置日志
log_level = config_manager.get_config("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level.upper()))
logger = logging.getLogger(__name__)

settings = get_settings()


class AuthMiddleware(BaseHTTPMiddleware):
    """全局认证中间件

    对 `/api/v1/*` 请求强制要求 Bearer token；白名单路径（登录、注册、
    验证码、忘记/重置密码、邮箱验证、刷新令牌、OpenAPI 文档）放行。
    缺失或无效 token 时返回 401。

    设计动机：原先完全依赖每路由 `Depends(get_current_user)`，遗漏了鉴权的
    路由会对匿名请求返回 200，构成越权访问风险（测试 `test_live_protected_
    collections_reject_anonymous_requests` 即为此回归）。中间件层兜底拦截。
    """

    WHITELIST_PREFIXES = (
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/captcha",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/refresh",
        "/api/v1/openapi.json",
        "/api/v1/docs",
        "/api/v1/redoc",
        # 健康检查端点需公开访问（监控/探活），不应要求认证
        "/api/v1/health",
    )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # 仅保护 /api/v1/* 路径；其余 (健康检查、根、静态资源) 放行
        if (
            not path.startswith("/api/v1")
            or request.method == "OPTIONS"
            or path == "/api/v1/openapi.json"
            or path.startswith(self.WHITELIST_PREFIXES)
        ):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "未提供有效的认证凭据"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = jwt_service.verify_token(token)
        except Exception:
            payload = None
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "无效或过期的访问令牌"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("启动应用...")
    
    try:
        # 初始化数据库
        await init_database()
        logger.info("数据库初始化完成")
        
        # 配置依赖注入服务
        logger.info("配置依赖注入服务...")
        configure_services()
        logger.info("依赖注入服务配置完成")
        
        # 初始化应用服务
        logger.info("初始化应用服务...")
        services_initialized = await initialize_application_services()
        if services_initialized:
            logger.info("应用服务初始化完成")
        else:
            logger.warning("部分应用服务初始化失败，但应用将继续启动")
        
        # 初始化缓存预热机制
        logger.info("初始化缓存预热机制...")
        try:
            from .tasks.cache_preheating_scheduler import start_cache_preheating_scheduler
            from .services.cache_preheating_service import start_cache_preheating
            from .services.cache_preheating_monitor import start_cache_preheating_monitoring
            
            # 启动预热服务
            await start_cache_preheating()
            logger.info("缓存预热服务启动完成")
            
            # 启动预热调度器
            await start_cache_preheating_scheduler()
            logger.info("缓存预热调度器启动完成")
            
            # 启动预热监控
            await start_cache_preheating_monitoring()
            logger.info("缓存预热监控启动完成")
            
        except Exception as e:
            logger.warning(f"缓存预热机制初始化失败: {e}")
            # 不阻止应用启动，预热机制是可选功能
        
        # 初始化百度文心一言服务
        logger.info("初始化百度文心一言服务...")
        try:
            from .services.baidu_wenxin_service import initialize_wenxin_service
            
            # 从配置管理器获取API密钥
            baidu_api_key = config_manager.get_config('BAIDU_API_KEY')
            baidu_secret_key = config_manager.get_config('BAIDU_SECRET_KEY')
            
            if baidu_api_key and baidu_secret_key:
                await initialize_wenxin_service(
                    api_key=baidu_api_key,
                    secret_key=baidu_secret_key,
                    api_endpoint=config_manager.get_config('BAIDU_BASE_URL')
                )
                logger.info("百度文心一言服务初始化完成")
            else:
                logger.info("百度文心一言API密钥未配置，跳过初始化")
                
        except Exception as e:
            logger.warning(f"百度文心一言服务初始化失败: {e}")
            # 不阻止应用启动，AI服务是可选功能
        
        # 初始化阿里通义千问服务
        logger.info("初始化阿里通义千问服务...")
        try:
            from .services.aliyun_tongyi_service import initialize_tongyi_service
            
            # 从配置管理器获取API密钥
            aliyun_api_key = config_manager.get_config('ALIYUN_API_KEY')
            
            if aliyun_api_key:
                await initialize_tongyi_service(
                    api_key=aliyun_api_key,
                    api_endpoint=config_manager.get_config('ALIYUN_API_ENDPOINT')
                )
                logger.info("阿里通义千问服务初始化完成")
            else:
                logger.info("阿里通义千问API密钥未配置，跳过初始化")
                
        except Exception as e:
            logger.warning(f"阿里通义千问服务初始化失败: {e}")
            # 不阻止应用启动，AI服务是可选功能
        
        yield
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        traceback.print_exc()
        raise
    finally:
        logger.info("关闭应用...")
        
        # 停止缓存预热机制
        try:
            from .tasks.cache_preheating_scheduler import stop_cache_preheating_scheduler
            from .services.cache_preheating_monitor import stop_cache_preheating_monitoring
            
            await stop_cache_preheating_scheduler()
            await stop_cache_preheating_monitoring()
            logger.info("缓存预热机制已停止")
        except Exception as e:
            logger.warning(f"停止缓存预热机制失败: {e}")
        
        try:
            await close_database()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")

# 获取API配置
api_config = config_manager.get_api_config()

app = FastAPI(
    title=api_config["project_name"],
    description="AI测试管理系统 - 用户管理模块API",
    version="1.0.0",
    openapi_url=f"{api_config['v1_str']}/openapi.json",
    docs_url=f"{api_config['v1_str']}/docs",
    redoc_url=f"{api_config['v1_str']}/redoc",
    lifespan=lifespan
)

# 设置依赖注入
setup_dependency_injection(app)

# 设置性能监控（必须在CORS之前添加）
performance_monitor = setup_performance_monitoring(app)
logger.info("Performance monitoring enabled - tracking response times to ensure 90% of requests complete within 5 seconds")

# 获取CORS配置并设置CORS
cors_config = config_manager.get_cors_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config["origins"],
    allow_credentials=cors_config["allow_credentials"],
    allow_methods=cors_config["allow_methods"],
    allow_headers=cors_config["allow_headers"],
)

# 全局认证中间件：拦截 /api/v1/* 请求，白名单放行认证/文档端点
app.add_middleware(AuthMiddleware)

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # FastAPI 的 HTTPException 已由其原生路由层处理；这里只兜底非 HTTP 异常，
    # 否则会把路由显式抛出的 404/400 等重新包装成 500，掩盖真实状态码。
    if isinstance(exc, HTTPException):
        raise exc
    """全局异常处理"""
    logger.error(f"未处理的异常: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "detail": str(exc) if settings.DEBUG else None
        }
    )

# 注册路由
app.include_router(api_router, prefix=api_config["v1_str"])

# 头像等运行时静态资源
static_dir = Path(__file__).resolve().parents[2] / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "message": "服务正常运行"}

# 根路径
@app.get("/", tags=["系统"])
async def root():
    return {"message": "AI测试管理系统 - 用户管理模块API", "version": "1.0.0"}

if __name__ == "__main__":
    # 获取服务器配置
    server_config = config_manager.get_server_config()
    
    uvicorn.run(
        "src.main:app",
        host=server_config["host"],
        port=server_config["port"],
        reload=server_config["debug"],
        log_level=server_config["log_level"].lower()
    )
