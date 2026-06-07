"""
AI助手权限管理服务
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from ..models.user import User, UserRole
from ..models.role import Role
from ..models.permission import RolePermission
from ..models.permission import Permission, PermissionType
from ..models.ai_chat_session import AIChatSession
from ..models.ai_model_config import AIModelConfig
from ..models.ai_prompt_template import AIPromptTemplate
from ..core.exceptions import PermissionError, ValidationError

logger = logging.getLogger(__name__)


class AIPermissionService:
    """AI助手权限管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # AI助手相关权限定义
        self.ai_permissions = {
            # 基础权限
            "ai_chat_basic": {
                "name": "AI基础对话",
                "description": "允许用户进行基础AI对话",
                "module": "ai_assistant",
                "type": PermissionType.FUNCTION,
                "resource": "ai_chat",
                "action": "basic_chat"
            },
            "ai_chat_advanced": {
                "name": "AI高级对话",
                "description": "允许用户使用高级AI功能和模型",
                "module": "ai_assistant", 
                "type": PermissionType.FUNCTION,
                "resource": "ai_chat",
                "action": "advanced_chat"
            },
            
            # 会话管理权限
            "ai_session_create": {
                "name": "创建AI会话",
                "description": "允许用户创建新的AI对话会话",
                "module": "ai_assistant",
                "type": PermissionType.OPERATION,
                "resource": "ai_session",
                "action": "create"
            },
            "ai_session_read": {
                "name": "查看AI会话",
                "description": "允许用户查看AI对话会话",
                "module": "ai_assistant",
                "type": PermissionType.OPERATION,
                "resource": "ai_session",
                "action": "read"
            },
            "ai_session_update": {
                "name": "编辑AI会话",
                "description": "允许用户编辑AI对话会话",
                "module": "ai_assistant",
                "type": PermissionType.OPERATION,
                "resource": "ai_session",
                "action": "update"
            },
            "ai_session_delete": {
                "name": "删除AI会话",
                "description": "允许用户删除AI对话会话",
                "module": "ai_assistant",
                "type": PermissionType.OPERATION,
                "resource": "ai_session",
                "action": "delete"
            },
            
            # 模型使用权限
            "ai_model_gpt4": {
                "name": "使用GPT-4模型",
                "description": "允许用户使用GPT-4系列模型",
                "module": "ai_assistant",
                "type": PermissionType.FUNCTION,
                "resource": "ai_model",
                "action": "use_gpt4"
            },
            "ai_model_claude": {
                "name": "使用Claude模型",
                "description": "允许用户使用Claude系列模型",
                "module": "ai_assistant",
                "type": PermissionType.FUNCTION,
                "resource": "ai_model",
                "action": "use_claude"
            },
            "ai_model_chinese": {
                "name": "使用中文AI模型",
                "description": "允许用户使用文心一言、通义千问等中文模型",
                "module": "ai_assistant",
                "type": PermissionType.FUNCTION,
                "resource": "ai_model",
                "action": "use_chinese"
            },
            
            # 提示词模板权限
            "ai_template_read": {
                "name": "查看提示词模板",
                "description": "允许用户查看提示词模板",
                "module": "ai_assistant",
                "type": PermissionType.OPERATION,
                "resource": "ai_template",
                "action": "read"
            },
            "ai_template_create": {
                "name": "创建提示词模板",
                "description": "允许用户创建提示词模板",
                "module": "ai_assistant",
                "type": PermissionType.OPERATION,
                "resource": "ai_template",
                "action": "create"
            },
            "ai_template_update": {
                "name": "编辑提示词模板",
                "description": "允许用户编辑提示词模板",
                "module": "ai_assistant",
                "type": PermissionType.OPERATION,
                "resource": "ai_template",
                "action": "update"
            },
            "ai_template_delete": {
                "name": "删除提示词模板",
                "description": "允许用户删除提示词模板",
                "module": "ai_assistant",
                "type": PermissionType.OPERATION,
                "resource": "ai_template",
                "action": "delete"
            },
            "ai_template_share": {
                "name": "分享提示词模板",
                "description": "允许用户分享提示词模板",
                "module": "ai_assistant",
                "type": PermissionType.OPERATION,
                "resource": "ai_template",
                "action": "share"
            },
            
            # 管理权限
            "ai_admin_config": {
                "name": "AI配置管理",
                "description": "允许管理员配置AI服务参数",
                "module": "ai_assistant",
                "type": PermissionType.MODULE,
                "resource": "ai_config",
                "action": "manage"
            },
            "ai_admin_monitor": {
                "name": "AI使用监控",
                "description": "允许管理员监控AI使用情况",
                "module": "ai_assistant",
                "type": PermissionType.MODULE,
                "resource": "ai_monitor",
                "action": "view"
            },
            "ai_admin_quota": {
                "name": "AI配额管理",
                "description": "允许管理员管理用户AI使用配额",
                "module": "ai_assistant",
                "type": PermissionType.MODULE,
                "resource": "ai_quota",
                "action": "manage"
            },
            
            # 高级功能权限
            "ai_suggestion_generate": {
                "name": "生成智能建议",
                "description": "允许用户使用AI生成智能建议功能",
                "module": "ai_assistant",
                "type": PermissionType.FUNCTION,
                "resource": "ai_suggestion",
                "action": "generate"
            },
            "ai_analysis_advanced": {
                "name": "高级分析功能",
                "description": "允许用户使用AI高级分析功能",
                "module": "ai_assistant",
                "type": PermissionType.FUNCTION,
                "resource": "ai_analysis",
                "action": "advanced"
            },
            "ai_file_upload": {
                "name": "AI文件上传",
                "description": "允许用户上传文件给AI分析",
                "module": "ai_assistant",
                "type": PermissionType.FUNCTION,
                "resource": "ai_file",
                "action": "upload"
            }
        }
    
    async def initialize_ai_permissions(self) -> Dict[str, Any]:
        """初始化AI助手相关权限"""
        try:
            created_permissions = []
            updated_permissions = []
            
            for code, perm_data in self.ai_permissions.items():
                # 检查权限是否已存在
                query = select(Permission).where(Permission.code == code)
                result = await self.db.execute(query)
                existing_permission = result.scalar_one_or_none()
                
                if existing_permission:
                    # 更新现有权限
                    existing_permission.name = perm_data["name"]
                    existing_permission.description = perm_data["description"]
                    existing_permission.module = perm_data["module"]
                    existing_permission.type = perm_data["type"]
                    existing_permission.resource = perm_data["resource"]
                    existing_permission.action = perm_data["action"]
                    updated_permissions.append(code)
                else:
                    # 创建新权限
                    new_permission = Permission(
                        code=code,
                        name=perm_data["name"],
                        description=perm_data["description"],
                        module=perm_data["module"],
                        type=perm_data["type"],
                        resource=perm_data["resource"],
                        action=perm_data["action"],
                        is_system_permission=True,
                        is_active=True,
                        sort_order=0
                    )
                    self.db.add(new_permission)
                    created_permissions.append(code)
            
            await self.db.commit()
            
            logger.info(f"AI权限初始化完成: 创建 {len(created_permissions)} 个, 更新 {len(updated_permissions)} 个")
            
            return {
                "success": True,
                "created_count": len(created_permissions),
                "updated_count": len(updated_permissions),
                "created_permissions": created_permissions,
                "updated_permissions": updated_permissions
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"AI权限初始化失败: {str(e)}")
            raise ValidationError(f"AI权限初始化失败: {str(e)}")
    
    async def check_user_ai_permission(self, user_id: int, permission_code: str) -> Tuple[bool, str]:
        """检查用户是否有指定的AI权限"""
        try:
            # 获取用户信息
            query = select(User).options(selectinload(User.roles)).where(User.id == user_id)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return False, "用户不存在"
            
            if not user.is_active:
                return False, "用户账户已禁用"
            
            # 超级用户拥有所有权限
            if user.is_superuser:
                return True, "超级用户权限"
            
            # 检查用户角色权限
            user_role_ids = [role.role_id for role in user.roles]
            if not user_role_ids:
                return False, "用户未分配角色"
            
            # 查询权限
            permission_query = select(Permission).where(Permission.code == permission_code)
            permission_result = await self.db.execute(permission_query)
            permission = permission_result.scalar_one_or_none()
            
            if not permission:
                return False, f"权限 {permission_code} 不存在"
            
            if not permission.is_active:
                return False, f"权限 {permission_code} 已禁用"
            
            # 检查角色是否有该权限
            role_permission_query = select(RolePermission).where(
                and_(
                    RolePermission.role_id.in_(user_role_ids),
                    RolePermission.permission_id == permission.id
                )
            )
            role_permission_result = await self.db.execute(role_permission_query)
            role_permission = role_permission_result.scalar_one_or_none()
            
            if role_permission:
                return True, "角色权限验证通过"
            
            return False, f"用户无 {permission_code} 权限"
            
        except Exception as e:
            logger.error(f"检查用户AI权限失败: {str(e)}")
            return False, f"权限检查失败: {str(e)}"
    
    async def check_ai_chat_permission(self, user_id: int, advanced: bool = False) -> Tuple[bool, str]:
        """检查用户AI对话权限"""
        if advanced:
            return await self.check_user_ai_permission(user_id, "ai_chat_advanced")
        else:
            # 检查基础权限或高级权限
            basic_check = await self.check_user_ai_permission(user_id, "ai_chat_basic")
            if basic_check[0]:
                return basic_check
            
            advanced_check = await self.check_user_ai_permission(user_id, "ai_chat_advanced")
            return advanced_check
    
    async def check_ai_model_permission(self, user_id: int, model_provider: str) -> Tuple[bool, str]:
        """检查用户AI模型使用权限"""
        # 根据模型提供商检查对应权限
        model_permission_map = {
            "openai": "ai_model_gpt4",
            "anthropic": "ai_model_claude",
            "baidu_wenxin": "ai_model_chinese",
            "aliyun_tongyi": "ai_model_chinese",
            "google_gemini": "ai_model_gpt4"  # 归类到GPT4权限
        }
        
        permission_code = model_permission_map.get(model_provider.lower())
        if not permission_code:
            return False, f"未知的AI模型提供商: {model_provider}"
        
        return await self.check_user_ai_permission(user_id, permission_code)
    
    async def check_ai_session_permission(self, user_id: int, action: str, session_id: Optional[int] = None) -> Tuple[bool, str]:
        """检查用户AI会话权限"""
        permission_code = f"ai_session_{action}"
        
        # 检查基础权限
        has_permission, message = await self.check_user_ai_permission(user_id, permission_code)
        if not has_permission:
            return has_permission, message
        
        # 如果是更新或删除操作，需要检查会话所有权
        if action in ["update", "delete"] and session_id:
            session_query = select(AIChatSession).where(AIChatSession.id == session_id)
            session_result = await self.db.execute(session_query)
            session = session_result.scalar_one_or_none()
            
            if not session:
                return False, "会话不存在"
            
            if session.user_id != user_id:
                # 检查是否有管理员权限
                admin_check = await self.check_user_ai_permission(user_id, "ai_admin_monitor")
                if not admin_check[0]:
                    return False, "无权限操作他人的会话"
        
        return True, "权限验证通过"
    
    async def check_ai_template_permission(self, user_id: int, action: str, template_id: Optional[int] = None) -> Tuple[bool, str]:
        """检查用户AI模板权限"""
        permission_code = f"ai_template_{action}"
        
        # 检查基础权限
        has_permission, message = await self.check_user_ai_permission(user_id, permission_code)
        if not has_permission:
            return has_permission, message
        
        # 如果是更新或删除操作，需要检查模板所有权
        if action in ["update", "delete"] and template_id:
            template_query = select(AIPromptTemplate).where(AIPromptTemplate.id == template_id)
            template_result = await self.db.execute(template_query)
            template = template_result.scalar_one_or_none()
            
            if not template:
                return False, "模板不存在"
            
            if template.user_id != user_id and not template.is_public:
                # 检查是否有管理员权限
                admin_check = await self.check_user_ai_permission(user_id, "ai_admin_config")
                if not admin_check[0]:
                    return False, "无权限操作他人的私有模板"
        
        return True, "权限验证通过"
    
    async def get_user_ai_permissions(self, user_id: int) -> Dict[str, Any]:
        """获取用户的AI相关权限"""
        try:
            permissions = {}
            
            for code, perm_data in self.ai_permissions.items():
                has_permission, _ = await self.check_user_ai_permission(user_id, code)
                permissions[code] = {
                    "has_permission": has_permission,
                    "name": perm_data["name"],
                    "description": perm_data["description"],
                    "module": perm_data["module"],
                    "resource": perm_data["resource"],
                    "action": perm_data["action"]
                }
            
            return {
                "user_id": user_id,
                "permissions": permissions,
                "summary": {
                    "total_permissions": len(permissions),
                    "granted_permissions": sum(1 for p in permissions.values() if p["has_permission"]),
                    "denied_permissions": sum(1 for p in permissions.values() if not p["has_permission"])
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户AI权限失败: {str(e)}")
            raise ValidationError(f"获取用户AI权限失败: {str(e)}")
    
    async def get_ai_permission_usage_stats(self) -> Dict[str, Any]:
        """获取AI权限使用统计"""
        try:
            stats = {}
            
            for code, perm_data in self.ai_permissions.items():
                # 获取权限信息
                permission_query = select(Permission).where(Permission.code == code)
                permission_result = await self.db.execute(permission_query)
                permission = permission_result.scalar_one_or_none()
                
                if not permission:
                    continue
                
                # 统计拥有该权限的角色数量
                role_count_query = select(func.count(RolePermission.role_id)).where(
                    RolePermission.permission_id == permission.id
                )
                role_count_result = await self.db.execute(role_count_query)
                role_count = role_count_result.scalar() or 0
                
                # 统计拥有该权限的用户数量（通过角色）
                user_count_query = select(func.count(func.distinct(UserRole.user_id))).select_from(
                    UserRole.join(RolePermission, UserRole.role_id == RolePermission.role_id)
                ).where(RolePermission.permission_id == permission.id)
                user_count_result = await self.db.execute(user_count_query)
                user_count = user_count_result.scalar() or 0
                
                stats[code] = {
                    "permission_name": perm_data["name"],
                    "permission_id": permission.id,
                    "role_count": role_count,
                    "user_count": user_count,
                    "is_active": permission.is_active
                }
            
            return {
                "permission_stats": stats,
                "summary": {
                    "total_ai_permissions": len(stats),
                    "active_permissions": sum(1 for s in stats.values() if s["is_active"]),
                    "total_role_assignments": sum(s["role_count"] for s in stats.values()),
                    "total_user_coverage": sum(s["user_count"] for s in stats.values())
                }
            }
            
        except Exception as e:
            logger.error(f"获取AI权限统计失败: {str(e)}")
            raise ValidationError(f"获取AI权限统计失败: {str(e)}")
    
    async def validate_ai_operation_permission(self, user_id: int, operation: str, **kwargs) -> None:
        """验证AI操作权限，如果无权限则抛出异常"""
        permission_checks = {
            "chat_basic": lambda: self.check_ai_chat_permission(user_id, advanced=False),
            "chat_advanced": lambda: self.check_ai_chat_permission(user_id, advanced=True),
            "model_use": lambda: self.check_ai_model_permission(user_id, kwargs.get("model_provider", "")),
            "session_create": lambda: self.check_ai_session_permission(user_id, "create"),
            "session_read": lambda: self.check_ai_session_permission(user_id, "read", kwargs.get("session_id")),
            "session_update": lambda: self.check_ai_session_permission(user_id, "update", kwargs.get("session_id")),
            "session_delete": lambda: self.check_ai_session_permission(user_id, "delete", kwargs.get("session_id")),
            "template_create": lambda: self.check_ai_template_permission(user_id, "create"),
            "template_read": lambda: self.check_ai_template_permission(user_id, "read"),
            "template_update": lambda: self.check_ai_template_permission(user_id, "update", kwargs.get("template_id")),
            "template_delete": lambda: self.check_ai_template_permission(user_id, "delete", kwargs.get("template_id")),
            "template_share": lambda: self.check_ai_template_permission(user_id, "share", kwargs.get("template_id")),
            "suggestion_generate": lambda: self.check_user_ai_permission(user_id, "ai_suggestion_generate"),
            "analysis_advanced": lambda: self.check_user_ai_permission(user_id, "ai_analysis_advanced"),
            "file_upload": lambda: self.check_user_ai_permission(user_id, "ai_file_upload"),
            "admin_config": lambda: self.check_user_ai_permission(user_id, "ai_admin_config"),
            "admin_monitor": lambda: self.check_user_ai_permission(user_id, "ai_admin_monitor"),
            "admin_quota": lambda: self.check_user_ai_permission(user_id, "ai_admin_quota")
        }
        
        check_func = permission_checks.get(operation)
        if not check_func:
            raise PermissionError(f"未知的AI操作类型: {operation}")
        
        has_permission, message = await check_func()
        if not has_permission:
            raise PermissionError(f"AI操作权限不足: {message}")