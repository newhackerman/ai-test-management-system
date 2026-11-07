from contextlib import asynccontextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging

from .config import settings

logger = logging.getLogger(__name__)

def _ensure_mysql_charset(url: str) -> str:
    if not url.startswith("mysql") or "charset=" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}charset=utf8mb4"


database_url = _ensure_mysql_charset(settings.DATABASE_URL)

# 创建异步数据库引擎 - 主要使用异步
try:
    async_engine = create_async_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.DEBUG,
        future=True
    )
except Exception as e:
    logger.warning(f"Failed to create async engine: {e}. Falling back to sync only.")
    async_engine = None

# 创建同步数据库引擎 - 仅用于表创建
sync_db_url = database_url.replace("mysql+asyncmy://", "mysql+pymysql://")
engine = create_engine(
    sync_db_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
    }
)

# 创建异步会话工厂
if async_engine:
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
else:
    AsyncSessionLocal = None

# 创建同步会话工厂 - 仅用于表创建
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def _ensure_test_execution_charset():
    """Keep existing MySQL execution tables compatible with Chinese user input."""
    if not engine.dialect.name.startswith("mysql"):
        return

    text_columns = (
        "actual_result",
        "failure_reason",
        "execution_notes",
        "test_environment",
        "browser_info",
        "os_info",
    )
    column_list = ", ".join(f"'{column}'" for column in text_columns)
    with engine.begin() as connection:
        rows = connection.execute(text(f"""
            SELECT column_name, character_set_name
            FROM information_schema.COLUMNS
            WHERE table_schema = DATABASE()
              AND table_name = 'test_executions'
              AND column_name IN ({column_list})
              AND character_set_name IS NOT NULL
              AND character_set_name <> 'utf8mb4'
        """)).fetchall()
        if rows:
            connection.execute(text(
                "ALTER TABLE test_executions "
                "CONVERT TO CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_unicode_ci"
            ))
            logger.info("test_executions 字符集已修复为 utf8mb4")


def _ensure_table_utf8mb4(table_name: str):
    """Convert existing MySQL text tables so Chinese content can be stored."""
    if not engine.dialect.name.startswith("mysql"):
        return

    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT table_collation
                FROM information_schema.TABLES
                WHERE table_schema = DATABASE()
                  AND table_name = :table_name
                """
            ),
            {"table_name": table_name},
        ).fetchone()
        if row and row[0] and not str(row[0]).startswith("utf8mb4"):
            connection.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    "CONVERT TO CHARACTER SET utf8mb4 "
                    "COLLATE utf8mb4_unicode_ci"
                )
            )
            logger.info("%s charset converted to utf8mb4", table_name)


# 获取同步数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 获取异步数据库会话
async def get_async_session():
    """异步数据库会话生成器。

    既被 FastAPI 的 Depends(get_async_session) 当作异步生成器依赖使用，
    也可通过 get_async_session_ctx() 作为异步上下文管理器使用。
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Async database engine not available")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_session_ctx():
    """异步数据库会话上下文管理器。

    用于 service/task 中需要 `async with ... as session:` 的场景。
    之所以独立于 get_async_session，是因为后者要保持为 async generator
    以兼容 FastAPI 的 Depends() 依赖注入。
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Async database engine not available")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 获取数据库会话 - 兼容性别名
async def get_db_session():
    """获取数据库会话 - 异步版本"""
    async for session in get_async_session():
        yield session


# 获取数据库会话 - 同步版本
def get_db_session_sync():
    """获取数据库会话 - 同步版本"""
    return get_db()


# 初始化数据库
async def init_database():
    """初始化数据库连接和表结构"""
    try:
        # 导入所有模型以确保表被创建（import src.models 会注册全部
        # 模型；audit / dashboard 不在 __init__ 的导出列表里，显式
        # import 子模块以注册 audit_logs / security_events 与 6 张
        # 仪表板表）。第 11 项收敛：启动建表与 rebuild_db.py 现在用
        # 同一份共享元数据做全量 create_all，不再分三处拼表。
        import src.models  # noqa: F401
        from ..models import audit as _audit_models  # noqa: F401
        from ..models import dashboard as _dashboard_models  # noqa: F401
        from ..models.base import Base as ModelBase

        # 创建所有表（与 ops/rebuild_db.py 的 create_all 同源）
        ModelBase.metadata.create_all(bind=engine)
        testmanager_table_names = [
            "test_plans",
            "test_phases",
            "test_resources",
            "test_cases",
            "automation_scripts",
            "test_executions",
            "defects",
            "defect_comments",
            "test_coverage",
        ]
        _ensure_test_execution_charset()
        for table_name in testmanager_table_names:
            _ensure_table_utf8mb4(table_name)
        _ensure_table_utf8mb4("system_notifications")
        logger.info("数据库表结构初始化完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        # 即使初始化失败也不阻止服务启动
        pass


# 关闭数据库连接
async def close_database():
    """关闭数据库连接"""
    try:
        engine.dispose()
        if async_engine:
            await async_engine.dispose()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")
