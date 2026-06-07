"""
权限工具类 - 提供权限检查和管理的辅助功能
"""
from typing import Set, Dict, Any, List, Optional, Tuple
from ..models.permission import Permission
from ..models.role import Role
from ..models.user import User


class PermissionUtils:
    """权限工具类"""
    
    @staticmethod
    def build_permission_tree(permissions: List[Permission]) -> Dict[str, Any]:
        """
        构建权限树结构
        
        Args:
            permissions: 权限列表
            
        Returns:
            权限树结构
        """
        tree = {}
        
        # 按模块分组
        for permission in permissions:
            module = permission.module
            if module not in tree:
                tree[module] = {
                    "name": module,
                    "actions": {}
                }
            
            # 按操作分组
            action = permission.action
            if action not in tree[module]["actions"]:
                tree[module]["actions"][action] = {
                    "name": action,
                    "permissions": []
                }
            
            # 添加权限
            tree[module]["actions"][action]["permissions"].append({
                "id": permission.id,
                "name": permission.name,
                "code": permission.code,
                "resource": permission.resource,
                "description": permission.description
            })
        
        # 转换为数组格式
        result = []
        for module, module_data in tree.items():
            module_item = {
                "name": module,
                "actions": []
            }
            
            for action, action_data in module_data["actions"].items():
                action_item = {
                    "name": action,
                    "permissions": action_data["permissions"]
                }
                module_item["actions"].append(action_item)
            
            result.append(module_item)
        
        return {
            "modules": result
        }
    
    @staticmethod
    def flatten_permission_codes(permissions: List[Permission]) -> Set[str]:
        """
        扁平化权限代码集合
        
        Args:
            permissions: 权限列表
            
        Returns:
            权限代码集合
        """
        return {permission.code for permission in permissions}
    
    @staticmethod
    def check_permission_match(
        required_permissions: Set[str],
        user_permissions: Set[str],
        match_type: str = "all"
    ) -> bool:
        """
        检查权限匹配
        
        Args:
            required_permissions: 需要的权限集合
            user_permissions: 用户拥有的权限集合
            match_type: 匹配类型，all（全部匹配）或 any（任一匹配）
            
        Returns:
            是否匹配
        """
        if match_type == "all":
            return required_permissions.issubset(user_permissions)
        elif match_type == "any":
            return not required_permissions.isdisjoint(user_permissions)
        else:
            return False
    
    @staticmethod
    def extract_resource_from_permission(permission_code: str) -> Optional[str]:
        """
        从权限代码中提取资源
        
        Args:
            permission_code: 权限代码
            
        Returns:
            资源名称
        """
        # 权限代码格式通常是 module:action:resource
        parts = permission_code.split(":")
        if len(parts) >= 3:
            return parts[2]
        return None
    
    @staticmethod
    def extract_module_from_permission(permission_code: str) -> Optional[str]:
        """
        从权限代码中提取模块
        
        Args:
            permission_code: 权限代码
            
        Returns:
            模块名称
        """
        # 权限代码格式通常是 module:action:resource
        parts = permission_code.split(":")
        if len(parts) >= 1:
            return parts[0]
        return None
    
    @staticmethod
    def extract_action_from_permission(permission_code: str) -> Optional[str]:
        """
        从权限代码中提取操作
        
        Args:
            permission_code: 权限代码
            
        Returns:
            操作名称
        """
        # 权限代码格式通常是 module:action:resource
        parts = permission_code.split(":")
        if len(parts) >= 2:
            return parts[1]
        return None
    
    @staticmethod
    def generate_permission_code(module: str, action: str, resource: str = None) -> str:
        """
        生成权限代码
        
        Args:
            module: 模块名称
            action: 操作名称
            resource: 资源名称
            
        Returns:
            权限代码
        """
        if resource:
            return f"{module}:{action}:{resource}"
        return f"{module}:{action}"
    
    @staticmethod
    def get_role_priority(roles: List[Role]) -> int:
        """
        获取用户角色优先级（取最高优先级）
        
        Args:
            roles: 角色列表
            
        Returns:
            最高优先级
        """
        if not roles:
            return 0
        
        # 优先级数值越小，优先级越高
        return min(role.priority for role in roles)
    
    @staticmethod
    def check_role_hierarchy(
        user_roles: List[Role],
        target_role: Role,
        hierarchy_type: str = "higher"
    ) -> bool:
        """
        检查角色层级关系
        
        Args:
            user_roles: 用户角色列表
            target_role: 目标角色
            hierarchy_type: 层级类型，higher（更高层级）或 lower（更低层级）
            
        Returns:
            是否满足层级关系
        """
        if not user_roles:
            return False
        
        # 获取用户最高优先级
        user_priority = PermissionUtils.get_role_priority(user_roles)
        
        if hierarchy_type == "higher":
            # 用户角色优先级需要高于目标角色
            return user_priority < target_role.priority
        elif hierarchy_type == "lower":
            # 用户角色优先级需要低于目标角色
            return user_priority > target_role.priority
        else:
            return False
    
    @staticmethod
    def filter_permissions_by_resource(
        permissions: List[Permission],
        resource: str
    ) -> List[Permission]:
        """
        根据资源过滤权限
        
        Args:
            permissions: 权限列表
            resource: 资源名称
            
        Returns:
            过滤后的权限列表
        """
        return [p for p in permissions if p.resource == resource]
    
    @staticmethod
    def filter_permissions_by_module(
        permissions: List[Permission],
        module: str
    ) -> List[Permission]:
        """
        根据模块过滤权限
        
        Args:
            permissions: 权限列表
            module: 模块名称
            
        Returns:
            过滤后的权限列表
        """
        return [p for p in permissions if p.module == module]
    
    @staticmethod
    def filter_permissions_by_action(
        permissions: List[Permission],
        action: str
    ) -> List[Permission]:
        """
        根据操作过滤权限
        
        Args:
            permissions: 权限列表
            action: 操作名称
            
        Returns:
            过滤后的权限列表
        """
        return [p for p in permissions if p.action == action]
    
    @staticmethod
    def get_user_effective_permissions(
        user_permissions: Set[str],
        role_permissions: Set[str]
    ) -> Set[str]:
        """
        获取用户有效权限（用户权限和角色权限的并集）
        
        Args:
            user_permissions: 用户直接权限
            role_permissions: 角色权限
            
        Returns:
            有效权限集合
        """
        return user_permissions.union(role_permissions)
    
    @staticmethod
    def check_admin_permission(roles: List[str]) -> bool:
        """
        检查是否具有管理员权限
        
        Args:
            roles: 角色代码列表
            
        Returns:
            是否具有管理员权限
        """
        return "admin" in roles
    
    @staticmethod
    def check_system_role_permission(user_roles: List[Role], target_role: Role) -> bool:
        """
        检查系统角色权限（只有系统角色可以管理系统角色）
        
        Args:
            user_roles: 用户角色列表
            target_role: 目标角色
            
        Returns:
            是否具有系统角色权限
        """
        # 如果目标角色不是系统角色，则不需要特殊权限
        if not target_role.is_system_role:
            return True
        
        # 检查用户是否拥有系统角色
        return any(role.is_system_role for role in user_roles)