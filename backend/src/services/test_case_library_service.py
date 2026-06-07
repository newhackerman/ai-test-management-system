"""
测试用例库管理和版本控制服务

本模块实现测试用例库的分层管理和版本控制功能，包括：
- 用例库的分层管理和权限控制
- 用例版本控制和变更历史追踪
- 用例复用和依赖关系管理
- 用例统计分析和质量度量
- 用例库的导入导出功能
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from enum import Enum
import logging
import json
import hashlib

from ..models.test_case import TestCase, TestCaseType, TestCasePriority, TestCaseStatus
from ..models.test_plan import TestPlan
from ..models.project import Project
from ..models.user import User
from ..core.exceptions import ValidationError, PermissionError, NotFoundError, BusinessLogicError
from ..services.permission_service import PermissionService
from ..services.test_case_service import TestCaseService
from ..utils.test_cache import TestCacheManager

logger = logging.getLogger(__name__)


class LibraryType(Enum):
    """用例库类型枚举"""
    PROJECT = "PROJECT"          # 项目用例库
    GLOBAL = "GLOBAL"           # 全局用例库
    TEMPLATE = "TEMPLATE"       # 模板用例库
    ARCHIVED = "ARCHIVED"       # 归档用例库


class VersionAction(Enum):
    """版本操作类型枚举"""
    CREATE = "CREATE"           # 创建
    UPDATE = "UPDATE"           # 更新
    COPY = "COPY"              # 复制
    MERGE = "MERGE"            # 合并
    ROLLBACK = "ROLLBACK"      # 回滚


class TestCaseVersion:
    """测试用例版本类"""
    
    def __init__(self, case_id: int, version: int, content: Dict[str, Any], 
                 action: VersionAction, user_id: int, comment: str = ""):
        self.case_id = case_id
        self.version = version
        self.content = content
        self.action = action
        self.user_id = user_id
        self.comment = comment
        self.created_at = datetime.utcnow()
        self.content_hash = self._calculate_content_hash(content)
    
    def _calculate_content_hash(self, content: Dict[str, Any]) -> str:
        """计算内容哈希"""
        content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'case_id': self.case_id,
            'version': self.version,
            'content': self.content,
            'action': self.action.value,
            'user_id': self.user_id,
            'comment': self.comment,
            'created_at': self.created_at.isoformat(),
            'content_hash': self.content_hash
        }


class TestCaseLibrary:
    """测试用例库类"""
    
    def __init__(self, library_id: str, name: str, library_type: LibraryType, 
                 project_id: Optional[int] = None, parent_id: Optional[str] = None):
        self.library_id = library_id
        self.name = name
        self.library_type = library_type
        self.project_id = project_id
        self.parent_id = parent_id
        self.description = ""
        self.tags = []
        self.permissions = {}
        self.statistics = {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'library_id': self.library_id,
            'name': self.name,
            'library_type': self.library_type.value,
            'project_id': self.project_id,
            'parent_id': self.parent_id,
            'description': self.description,
            'tags': self.tags,
            'permissions': self.permissions,
            'statistics': self.statistics,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class TestCaseLibraryService:
    """测试用例库管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.permission_service = PermissionService(db)
        self.test_case_service = TestCaseService(db)
        self.cache_manager = TestCacheManager()
        
        # 内存存储（实际应用中应该使用数据库）
        self.libraries = {}
        self.versions = {}  # case_id -> List[TestCaseVersion]
        self.dependencies = {}  # case_id -> List[case_id]
        
        self._init_default_libraries()
    
    def _init_default_libraries(self):
        """初始化默认用例库"""
        # 全局模板库
        global_template = TestCaseLibrary(
            'global_template',
            '全局模板库',
            LibraryType.TEMPLATE
        )
        global_template.description = '系统级测试用例模板库'
        self.libraries['global_template'] = global_template
        
        # 归档库
        archived_lib = TestCaseLibrary(
            'archived',
            '归档用例库',
            LibraryType.ARCHIVED
        )
        archived_lib.description = '已归档的测试用例'
        self.libraries['archived'] = archived_lib
    
    async def create_library(
        self, 
        library_data: Dict[str, Any], 
        user_id: int
    ) -> TestCaseLibrary:
        """
        创建用例库
        
        Args:
            library_data: 用例库数据
            user_id: 创建用户ID
            
        Returns:
            TestCaseLibrary: 创建的用例库对象
        """
        try:
            # 1. 验证创建权限
            await self._validate_create_library_permission(user_id, library_data)
            
            # 2. 验证库数据
            await self._validate_library_data(library_data)
            
            # 3. 生成库ID
            library_id = self._generate_library_id(library_data)
            
            # 4. 创建用例库对象
            library = TestCaseLibrary(
                library_id=library_id,
                name=library_data['name'],
                library_type=LibraryType(library_data['library_type']),
                project_id=library_data.get('project_id'),
                parent_id=library_data.get('parent_id')
            )
            
            library.description = library_data.get('description', '')
            library.tags = library_data.get('tags', [])
            
            # 5. 设置权限
            library.permissions = {
                'owner': user_id,
                'readers': library_data.get('readers', []),
                'writers': library_data.get('writers', []),
                'admins': library_data.get('admins', [user_id])
            }
            
            # 6. 保存用例库
            self.libraries[library_id] = library
            
            # 7. 初始化统计信息
            await self._init_library_statistics(library_id)
            
            logger.info(f"用例库创建成功: {library_id}, 创建人: {user_id}")
            
            return library
            
        except Exception as e:
            logger.error(f"创建用例库失败: {str(e)}")
            raise
    
    async def get_library_by_id(self, library_id: str) -> Optional[TestCaseLibrary]:
        """
        根据ID获取用例库
        
        Args:
            library_id: 用例库ID
            
        Returns:
            Optional[TestCaseLibrary]: 用例库对象或None
        """
        return self.libraries.get(library_id)
    
    async def get_libraries_by_project(
        self, 
        project_id: int, 
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TestCaseLibrary], int]:
        """
        获取项目的用例库列表
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            page: 页码
            page_size: 每页大小
            
        Returns:
            Tuple[List[TestCaseLibrary], int]: 用例库列表和总数
        """
        # 过滤项目相关的用例库
        project_libraries = []
        for library in self.libraries.values():
            if library.project_id == project_id:
                # 检查访问权限
                if await self._check_library_access_permission(user_id, library):
                    project_libraries.append(library)
        
        # 排序
        project_libraries.sort(key=lambda x: x.updated_at, reverse=True)
        
        # 分页
        total = len(project_libraries)
        start = (page - 1) * page_size
        end = start + page_size
        
        return project_libraries[start:end], total
    
    async def get_global_libraries(
        self, 
        user_id: int,
        library_type: Optional[LibraryType] = None
    ) -> List[TestCaseLibrary]:
        """
        获取全局用例库列表
        
        Args:
            user_id: 用户ID
            library_type: 库类型过滤
            
        Returns:
            List[TestCaseLibrary]: 用例库列表
        """
        global_libraries = []
        for library in self.libraries.values():
            if library.project_id is None:  # 全局库
                if library_type is None or library.library_type == library_type:
                    if await self._check_library_access_permission(user_id, library):
                        global_libraries.append(library)
        
        return sorted(global_libraries, key=lambda x: x.updated_at, reverse=True)
    
    async def add_case_to_library(
        self, 
        library_id: str, 
        case_id: int, 
        user_id: int,
        copy_mode: bool = False
    ) -> bool:
        """
        添加用例到库
        
        Args:
            library_id: 用例库ID
            case_id: 用例ID
            user_id: 用户ID
            copy_mode: 是否复制模式
            
        Returns:
            bool: 是否成功
        """
        try:
            # 1. 验证权限
            library = await self.get_library_by_id(library_id)
            if not library:
                raise NotFoundError("用例库不存在")
            
            if not await self._check_library_write_permission(user_id, library):
                raise PermissionError("没有写入权限")
            
            # 2. 获取用例
            test_case = await self.test_case_service.get_test_case_by_id(case_id)
            if not test_case:
                raise NotFoundError("测试用例不存在")
            
            # 3. 复制模式处理
            if copy_mode:
                # 复制用例到库
                copied_case = await self.test_case_service.copy_test_case(
                    case_id, None, user_id
                )
                case_id = copied_case.id
            
            # 4. 创建版本记录
            await self._create_version_record(
                case_id, test_case.to_dict(), VersionAction.CREATE, user_id,
                f"添加到用例库: {library.name}"
            )
            
            # 5. 更新库统计
            await self._update_library_statistics(library_id)
            
            logger.info(f"用例添加到库成功: 用例{case_id} -> 库{library_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"添加用例到库失败: {str(e)}")
            raise
    
    async def create_case_version(
        self, 
        case_id: int, 
        user_id: int,
        comment: str = ""
    ) -> TestCaseVersion:
        """
        创建用例版本
        
        Args:
            case_id: 用例ID
            user_id: 用户ID
            comment: 版本注释
            
        Returns:
            TestCaseVersion: 版本对象
        """
        try:
            # 1. 获取当前用例
            test_case = await self.test_case_service.get_test_case_by_id(case_id)
            if not test_case:
                raise NotFoundError("测试用例不存在")
            
            # 2. 获取下一个版本号
            next_version = await self._get_next_version_number(case_id)
            
            # 3. 创建版本记录
            version = await self._create_version_record(
                case_id, test_case.to_dict(), VersionAction.UPDATE, user_id, comment
            )
            
            logger.info(f"用例版本创建成功: 用例{case_id}, 版本{next_version}")
            
            return version
            
        except Exception as e:
            logger.error(f"创建用例版本失败: {str(e)}")
            raise
    
    async def get_case_versions(
        self, 
        case_id: int,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[TestCaseVersion], int]:
        """
        获取用例版本历史
        
        Args:
            case_id: 用例ID
            page: 页码
            page_size: 每页大小
            
        Returns:
            Tuple[List[TestCaseVersion], int]: 版本列表和总数
        """
        versions = self.versions.get(case_id, [])
        
        # 按版本号倒序排列
        versions.sort(key=lambda x: x.version, reverse=True)
        
        # 分页
        total = len(versions)
        start = (page - 1) * page_size
        end = start + page_size
        
        return versions[start:end], total
    
    async def rollback_case_version(
        self, 
        case_id: int, 
        target_version: int, 
        user_id: int
    ) -> TestCase:
        """
        回滚用例版本
        
        Args:
            case_id: 用例ID
            target_version: 目标版本号
            user_id: 用户ID
            
        Returns:
            TestCase: 回滚后的用例对象
        """
        try:
            # 1. 获取目标版本
            target_version_obj = await self._get_version_by_number(case_id, target_version)
            if not target_version_obj:
                raise NotFoundError(f"版本 {target_version} 不存在")
            
            # 2. 验证权限
            test_case = await self.test_case_service.get_test_case_by_id(case_id)
            if not test_case:
                raise NotFoundError("测试用例不存在")
            
            # 3. 应用版本内容
            version_content = target_version_obj.content
            updated_case = await self.test_case_service.update_test_case(
                case_id, version_content, user_id
            )
            
            # 4. 创建回滚版本记录
            await self._create_version_record(
                case_id, version_content, VersionAction.ROLLBACK, user_id,
                f"回滚到版本 {target_version}"
            )
            
            logger.info(f"用例版本回滚成功: 用例{case_id}, 回滚到版本{target_version}")
            
            return updated_case
            
        except Exception as e:
            logger.error(f"回滚用例版本失败: {str(e)}")
            raise
    
    async def compare_case_versions(
        self, 
        case_id: int, 
        version1: int, 
        version2: int
    ) -> Dict[str, Any]:
        """
        比较用例版本
        
        Args:
            case_id: 用例ID
            version1: 版本1
            version2: 版本2
            
        Returns:
            Dict[str, Any]: 比较结果
        """
        try:
            # 1. 获取两个版本
            v1_obj = await self._get_version_by_number(case_id, version1)
            v2_obj = await self._get_version_by_number(case_id, version2)
            
            if not v1_obj or not v2_obj:
                raise NotFoundError("指定版本不存在")
            
            # 2. 比较内容
            differences = self._compare_version_content(v1_obj.content, v2_obj.content)
            
            return {
                'case_id': case_id,
                'version1': version1,
                'version2': version2,
                'differences': differences,
                'summary': self._generate_diff_summary(differences)
            }
            
        except Exception as e:
            logger.error(f"比较用例版本失败: {str(e)}")
            raise
    
    async def create_case_dependency(
        self, 
        source_case_id: int, 
        target_case_id: int, 
        dependency_type: str,
        user_id: int
    ) -> bool:
        """
        创建用例依赖关系
        
        Args:
            source_case_id: 源用例ID
            target_case_id: 目标用例ID
            dependency_type: 依赖类型 (prerequisite, related, derived)
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        try:
            # 1. 验证用例存在
            source_case = await self.test_case_service.get_test_case_by_id(source_case_id)
            target_case = await self.test_case_service.get_test_case_by_id(target_case_id)
            
            if not source_case or not target_case:
                raise NotFoundError("用例不存在")
            
            # 2. 检查循环依赖
            if await self._check_circular_dependency(source_case_id, target_case_id):
                raise BusinessLogicError("创建依赖会形成循环依赖")
            
            # 3. 创建依赖关系
            if source_case_id not in self.dependencies:
                self.dependencies[source_case_id] = []
            
            dependency = {
                'target_case_id': target_case_id,
                'dependency_type': dependency_type,
                'created_by': user_id,
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.dependencies[source_case_id].append(dependency)
            
            logger.info(f"用例依赖创建成功: {source_case_id} -> {target_case_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"创建用例依赖失败: {str(e)}")
            raise
    
    async def get_case_dependencies(
        self, 
        case_id: int,
        dependency_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用例依赖关系
        
        Args:
            case_id: 用例ID
            dependency_type: 依赖类型过滤
            
        Returns:
            List[Dict[str, Any]]: 依赖关系列表
        """
        dependencies = self.dependencies.get(case_id, [])
        
        if dependency_type:
            dependencies = [
                dep for dep in dependencies 
                if dep['dependency_type'] == dependency_type
            ]
        
        # 补充目标用例信息
        enriched_dependencies = []
        for dep in dependencies:
            target_case = await self.test_case_service.get_test_case_by_id(
                dep['target_case_id']
            )
            if target_case:
                enriched_dep = dep.copy()
                enriched_dep['target_case_title'] = target_case.case_title
                enriched_dep['target_case_code'] = target_case.case_code
                enriched_dependencies.append(enriched_dep)
        
        return enriched_dependencies
    
    async def get_library_statistics(self, library_id: str) -> Dict[str, Any]:
        """
        获取用例库统计信息
        
        Args:
            library_id: 用例库ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        library = await self.get_library_by_id(library_id)
        if not library:
            raise NotFoundError("用例库不存在")
        
        # 获取库中的用例
        library_cases = await self._get_library_cases(library_id)
        
        # 统计信息
        total_cases = len(library_cases)
        case_types = {}
        priorities = {}
        statuses = {}
        
        for case in library_cases:
            # 用例类型统计
            case_type = case.case_type.value if case.case_type else 'UNKNOWN'
            case_types[case_type] = case_types.get(case_type, 0) + 1
            
            # 优先级统计
            priority = case.priority.value if case.priority else 'UNKNOWN'
            priorities[priority] = priorities.get(priority, 0) + 1
            
            # 状态统计
            status = case.status.value if case.status else 'UNKNOWN'
            statuses[status] = statuses.get(status, 0) + 1
        
        # 质量度量
        quality_metrics = await self._calculate_library_quality_metrics(library_cases)
        
        statistics = {
            'library_id': library_id,
            'library_name': library.name,
            'total_cases': total_cases,
            'case_type_distribution': case_types,
            'priority_distribution': priorities,
            'status_distribution': statuses,
            'quality_metrics': quality_metrics,
            'last_updated': library.updated_at.isoformat(),
            'creation_trend': await self._get_case_creation_trend(library_cases)
        }
        
        # 更新库的统计信息
        library.statistics = statistics
        
        return statistics
    
    async def export_library(
        self, 
        library_id: str, 
        export_format: str = "json",
        user_id: int = None
    ) -> Dict[str, Any]:
        """
        导出用例库
        
        Args:
            library_id: 用例库ID
            export_format: 导出格式 (json, excel, csv)
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 导出结果
        """
        try:
            # 1. 验证权限
            library = await self.get_library_by_id(library_id)
            if not library:
                raise NotFoundError("用例库不存在")
            
            if user_id and not await self._check_library_access_permission(user_id, library):
                raise PermissionError("没有访问权限")
            
            # 2. 获取库中的用例
            library_cases = await self._get_library_cases(library_id)
            
            # 3. 准备导出数据
            export_data = {
                'library_info': library.to_dict(),
                'export_time': datetime.utcnow().isoformat(),
                'total_cases': len(library_cases),
                'cases': []
            }
            
            for case in library_cases:
                case_data = case.to_dict()
                
                # 添加版本信息
                versions = await self.get_case_versions(case.id)
                case_data['versions'] = [v.to_dict() for v in versions[0]]
                
                # 添加依赖信息
                dependencies = await self.get_case_dependencies(case.id)
                case_data['dependencies'] = dependencies
                
                export_data['cases'].append(case_data)
            
            # 4. 格式化导出数据
            if export_format == "json":
                return export_data
            elif export_format == "excel":
                return await self._export_to_excel(export_data)
            elif export_format == "csv":
                return await self._export_to_csv(export_data)
            else:
                raise ValidationError(f"不支持的导出格式: {export_format}")
            
        except Exception as e:
            logger.error(f"导出用例库失败: {str(e)}")
            raise
    
    async def import_library(
        self, 
        import_data: Dict[str, Any], 
        target_library_id: Optional[str],
        user_id: int,
        import_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        导入用例库
        
        Args:
            import_data: 导入数据
            target_library_id: 目标库ID
            user_id: 用户ID
            import_options: 导入选项
            
        Returns:
            Dict[str, Any]: 导入结果
        """
        try:
            if not import_options:
                import_options = {
                    'merge_mode': 'skip',  # skip, overwrite, merge
                    'preserve_versions': True,
                    'preserve_dependencies': True
                }
            
            import_result = {
                'total_cases': 0,
                'imported_cases': 0,
                'skipped_cases': 0,
                'failed_cases': 0,
                'errors': []
            }
            
            # 1. 验证导入数据
            if 'cases' not in import_data:
                raise ValidationError("导入数据格式错误")
            
            # 2. 处理目标库
            if target_library_id:
                target_library = await self.get_library_by_id(target_library_id)
                if not target_library:
                    raise NotFoundError("目标用例库不存在")
                
                if not await self._check_library_write_permission(user_id, target_library):
                    raise PermissionError("没有写入权限")
            
            # 3. 导入用例
            import_result['total_cases'] = len(import_data['cases'])
            
            for case_data in import_data['cases']:
                try:
                    # 检查用例是否已存在
                    existing_case = await self._find_existing_case(case_data)
                    
                    if existing_case:
                        if import_options['merge_mode'] == 'skip':
                            import_result['skipped_cases'] += 1
                            continue
                        elif import_options['merge_mode'] == 'overwrite':
                            # 更新现有用例
                            await self.test_case_service.update_test_case(
                                existing_case.id, case_data, user_id
                            )
                        elif import_options['merge_mode'] == 'merge':
                            # 合并用例数据
                            merged_data = await self._merge_case_data(existing_case, case_data)
                            await self.test_case_service.update_test_case(
                                existing_case.id, merged_data, user_id
                            )
                    else:
                        # 创建新用例
                        new_case = await self.test_case_service.create_test_case(
                            case_data, user_id
                        )
                        
                        # 添加到目标库
                        if target_library_id:
                            await self.add_case_to_library(
                                target_library_id, new_case.id, user_id
                            )
                    
                    import_result['imported_cases'] += 1
                    
                except Exception as e:
                    import_result['failed_cases'] += 1
                    import_result['errors'].append({
                        'case_title': case_data.get('case_title', '未知'),
                        'error': str(e)
                    })
                    logger.warning(f"导入用例失败: {case_data.get('case_title', '未知')}, 错误: {str(e)}")
            
            logger.info(f"用例库导入完成: 成功{import_result['imported_cases']}, 失败{import_result['failed_cases']}")
            
            return import_result
            
        except Exception as e:
            logger.error(f"导入用例库失败: {str(e)}")
            raise    
# 私有方法
    def _generate_library_id(self, library_data: Dict[str, Any]) -> str:
        """生成用例库ID"""
        name = library_data['name']
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"lib_{name.lower().replace(' ', '_')}_{timestamp}"
    
    async def _validate_library_data(self, library_data: Dict[str, Any]) -> None:
        """验证用例库数据"""
        required_fields = ['name', 'library_type']
        for field in required_fields:
            if not library_data.get(field):
                raise ValidationError(f"字段 {field} 不能为空")
        
        # 验证库类型
        try:
            LibraryType(library_data['library_type'])
        except ValueError:
            raise ValidationError("无效的用例库类型")
    
    async def _validate_create_library_permission(self, user_id: int, library_data: Dict[str, Any]) -> None:
        """验证创建用例库权限"""
        # 项目库需要项目权限
        if library_data.get('project_id'):
            has_permission = await self.permission_service.check_project_permission(
                user_id, library_data['project_id'], 'test_library_create'
            )
            if not has_permission:
                raise PermissionError("没有创建项目用例库的权限")
        
        # 全局库需要系统权限
        else:
            has_permission = await self.permission_service.check_system_permission(
                user_id, 'global_library_create'
            )
            if not has_permission:
                raise PermissionError("没有创建全局用例库的权限")
    
    async def _check_library_access_permission(self, user_id: int, library: TestCaseLibrary) -> bool:
        """检查用例库访问权限"""
        # 检查库权限
        if user_id == library.permissions.get('owner'):
            return True
        
        if user_id in library.permissions.get('admins', []):
            return True
        
        if user_id in library.permissions.get('readers', []):
            return True
        
        if user_id in library.permissions.get('writers', []):
            return True
        
        # 检查项目权限
        if library.project_id:
            return await self.permission_service.check_project_permission(
                user_id, library.project_id, 'test_library_read'
            )
        
        return False
    
    async def _check_library_write_permission(self, user_id: int, library: TestCaseLibrary) -> bool:
        """检查用例库写入权限"""
        # 检查库权限
        if user_id == library.permissions.get('owner'):
            return True
        
        if user_id in library.permissions.get('admins', []):
            return True
        
        if user_id in library.permissions.get('writers', []):
            return True
        
        # 检查项目权限
        if library.project_id:
            return await self.permission_service.check_project_permission(
                user_id, library.project_id, 'test_library_write'
            )
        
        return False
    
    async def _init_library_statistics(self, library_id: str) -> None:
        """初始化用例库统计信息"""
        library = self.libraries.get(library_id)
        if library:
            library.statistics = {
                'total_cases': 0,
                'case_type_distribution': {},
                'priority_distribution': {},
                'status_distribution': {},
                'quality_score': 0.0,
                'last_updated': datetime.utcnow().isoformat()
            }
    
    async def _update_library_statistics(self, library_id: str) -> None:
        """更新用例库统计信息"""
        try:
            await self.get_library_statistics(library_id)
        except Exception as e:
            logger.warning(f"更新库统计信息失败: {str(e)}")
    
    async def _create_version_record(
        self, 
        case_id: int, 
        content: Dict[str, Any], 
        action: VersionAction, 
        user_id: int,
        comment: str = ""
    ) -> TestCaseVersion:
        """创建版本记录"""
        next_version = await self._get_next_version_number(case_id)
        
        version = TestCaseVersion(
            case_id=case_id,
            version=next_version,
            content=content,
            action=action,
            user_id=user_id,
            comment=comment
        )
        
        if case_id not in self.versions:
            self.versions[case_id] = []
        
        self.versions[case_id].append(version)
        
        return version
    
    async def _get_next_version_number(self, case_id: int) -> int:
        """获取下一个版本号"""
        versions = self.versions.get(case_id, [])
        if not versions:
            return 1
        
        max_version = max(v.version for v in versions)
        return max_version + 1
    
    async def _get_version_by_number(self, case_id: int, version_number: int) -> Optional[TestCaseVersion]:
        """根据版本号获取版本"""
        versions = self.versions.get(case_id, [])
        for version in versions:
            if version.version == version_number:
                return version
        return None
    
    def _compare_version_content(self, content1: Dict[str, Any], content2: Dict[str, Any]) -> List[Dict[str, Any]]:
        """比较版本内容"""
        differences = []
        
        # 比较所有字段
        all_keys = set(content1.keys()) | set(content2.keys())
        
        for key in all_keys:
            value1 = content1.get(key)
            value2 = content2.get(key)
            
            if value1 != value2:
                differences.append({
                    'field': key,
                    'old_value': value1,
                    'new_value': value2,
                    'change_type': self._get_change_type(value1, value2)
                })
        
        return differences
    
    def _get_change_type(self, old_value: Any, new_value: Any) -> str:
        """获取变更类型"""
        if old_value is None:
            return 'added'
        elif new_value is None:
            return 'removed'
        else:
            return 'modified'
    
    def _generate_diff_summary(self, differences: List[Dict[str, Any]]) -> str:
        """生成差异摘要"""
        if not differences:
            return "无变更"
        
        added = len([d for d in differences if d['change_type'] == 'added'])
        removed = len([d for d in differences if d['change_type'] == 'removed'])
        modified = len([d for d in differences if d['change_type'] == 'modified'])
        
        summary_parts = []
        if added > 0:
            summary_parts.append(f"新增{added}个字段")
        if removed > 0:
            summary_parts.append(f"删除{removed}个字段")
        if modified > 0:
            summary_parts.append(f"修改{modified}个字段")
        
        return "，".join(summary_parts)
    
    async def _check_circular_dependency(self, source_id: int, target_id: int) -> bool:
        """检查循环依赖"""
        visited = set()
        
        def dfs(current_id: int) -> bool:
            if current_id == source_id:
                return True
            
            if current_id in visited:
                return False
            
            visited.add(current_id)
            
            dependencies = self.dependencies.get(current_id, [])
            for dep in dependencies:
                if dfs(dep['target_case_id']):
                    return True
            
            return False
        
        return dfs(target_id)
    
    async def _get_library_cases(self, library_id: str) -> List[TestCase]:
        """获取用例库中的用例"""
        # 这里应该根据实际的库-用例关联关系查询
        # 简化实现，返回空列表
        return []
    
    async def _calculate_library_quality_metrics(self, cases: List[TestCase]) -> Dict[str, Any]:
        """计算用例库质量指标"""
        if not cases:
            return {
                'completeness_score': 0.0,
                'consistency_score': 0.0,
                'coverage_score': 0.0,
                'overall_quality_score': 0.0
            }
        
        # 完整性评分
        complete_cases = len([c for c in cases if c.test_steps and c.expected_result])
        completeness_score = (complete_cases / len(cases)) * 100
        
        # 一致性评分（简化计算）
        consistency_score = 85.0  # 假设值
        
        # 覆盖率评分（简化计算）
        coverage_score = 80.0  # 假设值
        
        # 总体质量评分
        overall_quality_score = (completeness_score + consistency_score + coverage_score) / 3
        
        return {
            'completeness_score': round(completeness_score, 2),
            'consistency_score': round(consistency_score, 2),
            'coverage_score': round(coverage_score, 2),
            'overall_quality_score': round(overall_quality_score, 2)
        }
    
    async def _get_case_creation_trend(self, cases: List[TestCase]) -> List[Dict[str, Any]]:
        """获取用例创建趋势"""
        # 按月统计用例创建数量
        monthly_counts = {}
        
        for case in cases:
            if case.created_at:
                month_key = case.created_at.strftime("%Y-%m")
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        
        # 转换为趋势数据
        trend_data = []
        for month, count in sorted(monthly_counts.items()):
            trend_data.append({
                'month': month,
                'count': count
            })
        
        return trend_data
    
    async def _export_to_excel(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """导出为Excel格式"""
        # 这里应该使用pandas或openpyxl生成Excel文件
        # 简化实现，返回数据结构
        return {
            'format': 'excel',
            'filename': f"test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            'data': export_data
        }
    
    async def _export_to_csv(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """导出为CSV格式"""
        # 这里应该生成CSV文件
        # 简化实现，返回数据结构
        return {
            'format': 'csv',
            'filename': f"test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            'data': export_data
        }
    
    async def _find_existing_case(self, case_data: Dict[str, Any]) -> Optional[TestCase]:
        """查找已存在的用例"""
        # 根据用例编码或标题查找
        case_code = case_data.get('case_code')
        case_title = case_data.get('case_title')
        
        if case_code:
            return await self.test_case_service.get_test_case_by_code(case_code)
        
        # 这里可以添加更复杂的匹配逻辑
        return None
    
    async def _merge_case_data(self, existing_case: TestCase, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """合并用例数据"""
        merged_data = existing_case.to_dict()
        
        # 合并策略：新数据覆盖旧数据，但保留重要字段
        important_fields = ['case_code', 'created_at', 'created_by']
        
        for key, value in new_data.items():
            if key not in important_fields and value is not None:
                merged_data[key] = value
        
        return merged_data