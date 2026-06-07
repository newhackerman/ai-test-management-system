"""
AI权限初始化服务
"""
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session
from ..services.ai_permission_service import AIPermissionService

logger = logging.getLogger(__name__)


class AIPermissionInitService:
    """AI权限初始化服务"""
    
    @staticmethod
    async def initialize_ai_permissions() -> Dict[str, Any]:
        """
        初始化AI权限
        
        在系统启动时自动创建AI相关权限
        """
        try:
            logger.info("开始初始化AI权限...")
            
            # 获取数据库会话
            async with get_db_session() as db:
                ai_permission_service = AIPermissionService(db)
                
                # 初始化AI权限
                result = await ai_permission_service.initialize_ai_permissions()
                
                logger.info(f"AI权限初始化完成: 创建 {result['created_count']} 个权限, "
                          f"更新 {result['updated_count']} 个权限")
                
                return {
                    "success": True,
                    "message": "AI权限初始化成功",
                    "data": result
                }
                
        except Exception as e:
            logger.error(f"AI权限初始化失败: {str(e)}")
            return {
                "success": False,
                "message": f"AI权限初始化失败: {str(e)}",
                "data": None
            }
    
    @staticmethod
    async def check_ai_permissions_status() -> Dict[str, Any]:
        """
        检查AI权限状态
        
        检查系统中AI权限是否已正确配置
        """
        try:
            async with get_db_session() as db:
                ai_permission_service = AIPermissionService(db)
                
                # 获取AI权限统计
                stats = await ai_permission_service.get_ai_permission_usage_stats()
                
                # 检查是否有AI权限
                total_ai_permissions = stats['summary']['total_ai_permissions']
                active_permissions = stats['summary']['active_permissions']
                
                if total_ai_permissions == 0:
                    return {
                        "status": "missing",
                        "message": "系统中没有AI权限，需要初始化",
                        "stats": stats
                    }
                elif active_permissions < total_ai_permissions:
                    return {
                        "status": "partial",
                        "message": f"部分AI权限未激活 ({active_permissions}/{total_ai_permissions})",
                        "stats": stats
                    }
                else:
                    return {
                        "status": "complete",
                        "message": f"AI权限配置完整 ({total_ai_permissions} 个权限)",
                        "stats": stats
                    }
                    
        except Exception as e:
            logger.error(f"检查AI权限状态失败: {str(e)}")
            return {
                "status": "error",
                "message": f"检查AI权限状态失败: {str(e)}",
                "stats": None
            }
    
    @staticmethod
    async def ensure_ai_permissions() -> Dict[str, Any]:
        """
        确保AI权限存在
        
        检查并在必要时初始化AI权限
        """
        try:
            # 检查权限状态
            status_result = await AIPermissionInitService.check_ai_permissions_status()
            
            if status_result["status"] in ["missing", "partial"]:
                logger.info(f"AI权限状态: {status_result['message']}, 开始初始化...")
                
                # 初始化权限
                init_result = await AIPermissionInitService.initialize_ai_permissions()
                
                if init_result["success"]:
                    logger.info("AI权限确保完成")
                    return {
                        "success": True,
                        "message": "AI权限已确保存在",
                        "action": "initialized",
                        "data": init_result["data"]
                    }
                else:
                    return {
                        "success": False,
                        "message": init_result["message"],
                        "action": "failed",
                        "data": None
                    }
            else:
                logger.info(f"AI权限状态正常: {status_result['message']}")
                return {
                    "success": True,
                    "message": "AI权限已存在，无需初始化",
                    "action": "skipped",
                    "data": status_result["stats"]
                }
                
        except Exception as e:
            logger.error(f"确保AI权限失败: {str(e)}")
            return {
                "success": False,
                "message": f"确保AI权限失败: {str(e)}",
                "action": "error",
                "data": None
            }