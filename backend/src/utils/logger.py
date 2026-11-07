"""项目统一日志工具。

多个模块（ai_file_storage、traceability_*、file_cleanup_task 等）引用
``from ..utils.logger import logger`` 或 ``get_logger``，但本文件曾经缺失，
导致引用它的模块一被加载就报 ModuleNotFoundError。main.py 已通过
logging.basicConfig 配置根日志，本模块只提供统一的获取入口。
"""
import logging

logger = logging.getLogger("ai_test_management_system")


def get_logger(name=None):
    """返回指定名称的 logger，默认项目根 logger。"""
    return logging.getLogger(name or "ai_test_management_system")
