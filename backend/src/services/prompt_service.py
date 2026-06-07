"""
提示词管理服务

本模块提供提示词模板的完整管理功能，包括：
1. 模板的创建、更新、删除和查询
2. 模板渲染和变量替换
3. 使用统计和评分管理
4. 模板分享和权限控制

技术特性：
- 支持Jinja2模板语法
- 变量验证和类型检查
- 使用统计和性能监控
- 权限控制和可见性管理
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..models.ai_prompt_template import AIPromptTemplate, AIPromptTemplateUsage, TemplateCategory, TemplateVisibility
from ..schemas.prompt_template import (
    PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateResponse,
    PromptTemplateListResponse, TemplateRenderRequest, TemplateRenderResponse,
    TemplateUsageCreate, TemplateUsageResponse, TemplateSearchRequest,
    TemplateStatistics, TemplateVariable
)

logger = logging.getLogger(__name__)
settings = get_settings()


class TemplateRenderer:
    """模板渲染器"""
    
    def __init__(self):
        self.builtin_functions = {
            'current_date': lambda: datetime.now().strftime('%Y-%m-%d'),
            'current_time': lambda: datetime.now().strftime('%H:%M:%S'),
            'current_datetime': lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_user': lambda ctx: ctx.get('user_name', 'Unknown'),
            'project_name': lambda ctx: ctx.get('project', {}).get('name', 'Unknown Project'),
            'user_role': lambda ctx: ctx.get('user_role', 'User')
        }
    
    async def render(self, template_content: str, context: Dict[str, Any], 
                    variables: Optional[List[TemplateVariable]] = None) -> Tuple[str, List[str], List[str]]:
        """
        渲染模板
        
        Args:
            template_content: 模板内容
            context: 渲染上下文
            variables: 模板变量定义
            
        Returns:
            Tuple[渲染后的内容, 使用的变量列表, 缺失的变量列表]
        """
        rendered = template_content
        variables_used = []
        missing_variables = []
        
        # 提取模板中的变量占位符
        placeholders = re.findall(r'\{(\w+)\}', template_content)
        
        # 替换变量占位符
        for placeholder in set(placeholders):
            placeholder_pattern = f"{{{placeholder}}}"
            
            if placeholder in context:
                # 替换用户提供的变量
                value = context[placeholder]
                rendered = rendered.replace(placeholder_pattern, str(value))
                variables_used.append(placeholder)
            elif placeholder in self.builtin_functions:
                # 替换内置函数
                try:
                    func = self.builtin_functions[placeholder]
                    if placeholder in ['current_user', 'project_name', 'user_role']:
                        result = func(context)
                    else:
                        result = func()
                    rendered = rendered.replace(placeholder_pattern, str(result))
                    variables_used.append(placeholder)
                except Exception as e:
                    logger.warning(f"Failed to execute builtin function {placeholder}: {e}")
                    rendered = rendered.replace(placeholder_pattern, f"[{placeholder} error]")
                    missing_variables.append(placeholder)
            else:
                # 检查是否是必需变量
                is_required = True
                if variables:
                    var_def = next((v for v in variables if v.name == placeholder), None)
                    if var_def and not var_def.required and var_def.default_value is not None:
                        # 使用默认值
                        rendered = rendered.replace(placeholder_pattern, str(var_def.default_value))
                        variables_used.append(placeholder)
                        is_required = False
                
                if is_required:
                    missing_variables.append(placeholder)
        
        return rendered, variables_used, missing_variables
    
    def validate_template_syntax(self, template_content: str) -> List[str]:
        """验证模板语法"""
        errors = []
        
        # 检查括号匹配
        open_braces = template_content.count('{')
        close_braces = template_content.count('}')
        if open_braces != close_braces:
            errors.append("模板中的大括号不匹配")
        
        # 检查变量名格式
        placeholders = re.findall(r'\{(\w+)\}', template_content)
        for placeholder in placeholders:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', placeholder):
                errors.append(f"变量名 '{placeholder}' 格式不正确")
        
        return errors


class PromptService:
    """提示词管理服务"""
    
    def __init__(self):
        self.renderer = TemplateRenderer()
    
    async def create_template(self, db: AsyncSession, template_data: PromptTemplateCreate, 
                            owner_id: int) -> AIPromptTemplate:
        """创建提示词模板"""
        # 验证模板名称唯一性（同一用户下）
        existing = await self._get_template_by_name(db, template_data.name, owner_id)
        if existing:
            raise ValueError(f"模板名称 '{template_data.name}' 已存在")
        
        # 验证模板语法
        syntax_errors = self.renderer.validate_template_syntax(template_data.content)
        if syntax_errors:
            raise ValueError(f"模板语法错误: {'; '.join(syntax_errors)}")
        
        # 创建模板
        template = AIPromptTemplate(
            name=template_data.name,
            title=template_data.title,
            description=template_data.description,
            category=template_data.category.value,
            subcategory=template_data.subcategory,
            content=template_data.content,
            variables=self._serialize_variables(template_data.variables),
            default_values=template_data.default_values,
            example_context=template_data.example_context,
            supported_providers=template_data.supported_providers,
            supported_models=template_data.supported_models,
            use_cases=template_data.use_cases,
            tags=template_data.tags,
            visibility=template_data.visibility.value,
            owner_id=owner_id,
            team_id=template_data.team_id
        )
        
        db.add(template)
        await db.commit()
        await db.refresh(template)
        
        logger.info(f"Created prompt template: {template.name} (ID: {template.id})")
        return template
    
    async def get_template(self, db: AsyncSession, template_id: int, 
                          user_id: Optional[int] = None) -> Optional[AIPromptTemplate]:
        """获取单个模板"""
        query = select(AIPromptTemplate).where(AIPromptTemplate.id == template_id)
        
        # 权限检查
        if user_id:
            query = query.where(
                or_(
                    AIPromptTemplate.owner_id == user_id,
                    AIPromptTemplate.visibility == TemplateVisibility.PUBLIC.value,
                    and_(
                        AIPromptTemplate.visibility == TemplateVisibility.TEAM.value,
                        AIPromptTemplate.team_id.isnot(None)
                        # TODO: 添加团队成员检查
                    )
                )
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_template(self, db: AsyncSession, template_id: int, 
                            template_data: PromptTemplateUpdate, user_id: int) -> AIPromptTemplate:
        """更新提示词模板"""
        template = await self.get_template(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        if template.owner_id != user_id:
            raise ValueError("只有模板所有者可以修改模板")
        
        # 验证新的模板语法（如果更新了内容）
        if template_data.content:
            syntax_errors = self.renderer.validate_template_syntax(template_data.content)
            if syntax_errors:
                raise ValueError(f"模板语法错误: {'; '.join(syntax_errors)}")
        
        # 更新字段
        update_data = template_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == 'variables':
                value = self._serialize_variables(value)
            elif field == 'category' and value:
                value = value.value
            elif field == 'visibility' and value:
                value = value.value
            
            setattr(template, field, value)
        
        template.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(template)
        
        logger.info(f"Updated prompt template: {template.name} (ID: {template.id})")
        return template
    
    async def delete_template(self, db: AsyncSession, template_id: int, user_id: int) -> bool:
        """删除提示词模板"""
        template = await self.get_template(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        if template.owner_id != user_id:
            raise ValueError("只有模板所有者可以删除模板")
        
        await db.delete(template)
        await db.commit()
        
        logger.info(f"Deleted prompt template: {template.name} (ID: {template.id})")
        return True
    
    async def search_templates(self, db: AsyncSession, search_request: TemplateSearchRequest,
                             user_id: Optional[int] = None) -> PromptTemplateListResponse:
        """搜索提示词模板"""
        query = select(AIPromptTemplate)
        
        # 权限过滤
        if user_id:
            query = query.where(
                or_(
                    AIPromptTemplate.owner_id == user_id,
                    AIPromptTemplate.visibility == TemplateVisibility.PUBLIC.value,
                    and_(
                        AIPromptTemplate.visibility == TemplateVisibility.TEAM.value,
                        AIPromptTemplate.team_id.isnot(None)
                        # TODO: 添加团队成员检查
                    )
                )
            )
        else:
            # 未登录用户只能看到公开模板
            query = query.where(AIPromptTemplate.visibility == TemplateVisibility.PUBLIC.value)
        
        # 搜索条件
        if search_request.query:
            search_term = f"%{search_request.query}%"
            query = query.where(
                or_(
                    AIPromptTemplate.name.ilike(search_term),
                    AIPromptTemplate.title.ilike(search_term),
                    AIPromptTemplate.description.ilike(search_term)
                )
            )
        
        if search_request.category:
            query = query.where(AIPromptTemplate.category == search_request.category.value)
        
        if search_request.visibility:
            query = query.where(AIPromptTemplate.visibility == search_request.visibility.value)
        
        if search_request.owner_id:
            query = query.where(AIPromptTemplate.owner_id == search_request.owner_id)
        
        if search_request.is_featured is not None:
            query = query.where(AIPromptTemplate.is_featured == search_request.is_featured)
        
        if search_request.is_verified is not None:
            query = query.where(AIPromptTemplate.is_verified == search_request.is_verified)
        
        if search_request.tags:
            # 标签搜索（JSON数组包含）
            for tag in search_request.tags:
                query = query.where(AIPromptTemplate.tags.contains([tag]))
        
        # 总数查询
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 排序
        sort_column = getattr(AIPromptTemplate, search_request.sort_by)
        if search_request.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # 分页
        offset = (search_request.page - 1) * search_request.size
        query = query.offset(offset).limit(search_request.size)
        
        result = await db.execute(query)
        templates = result.scalars().all()
        
        # 转换为响应格式
        template_responses = [
            PromptTemplateResponse.from_orm(template) for template in templates
        ]
        
        pages = ceil(total / search_request.size) if total > 0 else 0
        
        return PromptTemplateListResponse(
            templates=template_responses,
            total=total,
            page=search_request.page,
            size=search_request.size,
            pages=pages
        )
    
    async def render_template(self, db: AsyncSession, template_id: int, 
                            context: Dict[str, Any], user_id: Optional[int] = None) -> TemplateRenderResponse:
        """渲染模板"""
        template = await self.get_template(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        # 解析变量定义
        variables = None
        if template.variables:
            variables = [TemplateVariable(**var) for var in template.variables]
        
        # 渲染模板
        rendered_content, variables_used, missing_variables = await self.renderer.render(
            template.content, context, variables
        )
        
        return TemplateRenderResponse(
            rendered_content=rendered_content,
            template_id=template.id,
            template_name=template.name,
            variables_used=variables_used,
            missing_variables=missing_variables
        )
    
    async def record_template_usage(self, db: AsyncSession, usage_data: TemplateUsageCreate,
                                  user_id: int) -> AIPromptTemplateUsage:
        """记录模板使用情况"""
        # 验证模板存在
        template = await self.get_template(db, usage_data.template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        # 创建使用记录
        usage = AIPromptTemplateUsage(
            template_id=usage_data.template_id,
            user_id=user_id,
            ai_provider=usage_data.ai_provider,
            ai_model=usage_data.ai_model,
            use_case=usage_data.use_case,
            success=usage_data.success,
            tokens_used=usage_data.tokens_used,
            response_time=usage_data.response_time,
            user_rating=usage_data.user_rating,
            user_feedback=usage_data.user_feedback,
            variable_values=usage_data.variable_values
        )
        
        db.add(usage)
        
        # 更新模板统计
        template.usage_count += 1
        template.last_used_at = datetime.utcnow()
        
        # 更新评分
        if usage_data.user_rating:
            if template.rating_count == 0:
                template.rating_avg = float(usage_data.user_rating)
                template.rating_count = 1
            else:
                total_rating = template.rating_avg * template.rating_count + usage_data.user_rating
                template.rating_count += 1
                template.rating_avg = total_rating / template.rating_count
        
        await db.commit()
        await db.refresh(usage)
        
        logger.info(f"Recorded template usage: template_id={usage_data.template_id}, user_id={user_id}")
        return usage
    
    async def get_template_statistics(self, db: AsyncSession, 
                                    user_id: Optional[int] = None) -> TemplateStatistics:
        """获取模板统计信息"""
        # 基础统计查询
        base_query = select(AIPromptTemplate)
        if user_id:
            base_query = base_query.where(
                or_(
                    AIPromptTemplate.owner_id == user_id,
                    AIPromptTemplate.visibility == TemplateVisibility.PUBLIC.value
                )
            )
        else:
            base_query = base_query.where(AIPromptTemplate.visibility == TemplateVisibility.PUBLIC.value)
        
        # 总数统计
        total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
        total_templates = total_result.scalar()
        
        # 可见性统计
        public_result = await db.execute(
            select(func.count()).where(AIPromptTemplate.visibility == TemplateVisibility.PUBLIC.value)
        )
        public_templates = public_result.scalar()
        
        private_result = await db.execute(
            select(func.count()).where(AIPromptTemplate.visibility == TemplateVisibility.PRIVATE.value)
        )
        private_templates = private_result.scalar()
        
        featured_result = await db.execute(
            select(func.count()).where(AIPromptTemplate.is_featured == True)
        )
        featured_templates = featured_result.scalar()
        
        # 分类分布
        category_result = await db.execute(
            select(AIPromptTemplate.category, func.count()).group_by(AIPromptTemplate.category)
        )
        category_distribution = {row[0]: row[1] for row in category_result.fetchall()}
        
        # 使用统计
        usage_result = await db.execute(
            select(func.sum(AIPromptTemplate.usage_count))
        )
        total_usage = usage_result.scalar() or 0
        
        usage_statistics = {
            "total_usage": total_usage,
            "avg_usage_per_template": total_usage / total_templates if total_templates > 0 else 0
        }
        
        # 热门模板（按使用次数）
        top_templates_query = base_query.order_by(desc(AIPromptTemplate.usage_count)).limit(5)
        top_result = await db.execute(top_templates_query)
        top_templates = [PromptTemplateResponse.from_orm(t) for t in top_result.scalars().all()]
        
        # 最新模板
        recent_templates_query = base_query.order_by(desc(AIPromptTemplate.created_at)).limit(5)
        recent_result = await db.execute(recent_templates_query)
        recent_templates = [PromptTemplateResponse.from_orm(t) for t in recent_result.scalars().all()]
        
        return TemplateStatistics(
            total_templates=total_templates,
            public_templates=public_templates,
            private_templates=private_templates,
            featured_templates=featured_templates,
            category_distribution=category_distribution,
            usage_statistics=usage_statistics,
            top_templates=top_templates,
            recent_templates=recent_templates
        )
    
    async def get_user_templates(self, db: AsyncSession, user_id: int, 
                               category: Optional[str] = None, include_public: bool = True,
                               page: int = 1, size: int = 20) -> PromptTemplateListResponse:
        """获取用户的提示词模板"""
        query = select(AIPromptTemplate)
        
        if include_public:
            query = query.where(
                or_(
                    AIPromptTemplate.owner_id == user_id,
                    AIPromptTemplate.visibility == TemplateVisibility.PUBLIC.value
                )
            )
        else:
            query = query.where(AIPromptTemplate.owner_id == user_id)
        
        if category:
            query = query.where(AIPromptTemplate.category == category)
        
        # 总数查询
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页和排序
        query = query.order_by(desc(AIPromptTemplate.updated_at))
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await db.execute(query)
        templates = result.scalars().all()
        
        template_responses = [
            PromptTemplateResponse.from_orm(template) for template in templates
        ]
        
        pages = ceil(total / size) if total > 0 else 0
        
        return PromptTemplateListResponse(
            templates=template_responses,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
    
    async def _get_template_by_name(self, db: AsyncSession, name: str, 
                                  owner_id: int) -> Optional[AIPromptTemplate]:
        """根据名称获取模板（同一用户下）"""
        query = select(AIPromptTemplate).where(
            and_(
                AIPromptTemplate.name == name,
                AIPromptTemplate.owner_id == owner_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    def _serialize_variables(self, variables: Optional[List[TemplateVariable]]) -> Optional[List[Dict]]:
        """序列化变量定义"""
        if not variables:
            return None
        
        return [var.dict() for var in variables]
    
    # ==================== 版本管理功能 ====================
    
    async def create_template_version(self, db: AsyncSession, template_id: int, 
                                    template_data: PromptTemplateUpdate, user_id: int) -> AIPromptTemplate:
        """创建模板新版本"""
        # 获取原模板
        original_template = await self.get_template(db, template_id, user_id)
        if not original_template:
            raise ValueError("原模板不存在或无权限访问")
        
        if original_template.owner_id != user_id:
            raise ValueError("只有模板所有者可以创建新版本")
        
        # 验证新版本的模板语法
        if template_data.content:
            syntax_errors = self.renderer.validate_template_syntax(template_data.content)
            if syntax_errors:
                raise ValueError(f"模板语法错误: {'; '.join(syntax_errors)}")
        
        # 生成新版本号
        new_version = await self._generate_next_version(db, template_id)
        
        # 将原模板标记为非最新版本
        original_template.is_latest_version = False
        
        # 创建新版本模板
        new_template = AIPromptTemplate(
            name=original_template.name,
            title=template_data.title or original_template.title,
            description=template_data.description or original_template.description,
            category=template_data.category.value if template_data.category else original_template.category,
            subcategory=template_data.subcategory or original_template.subcategory,
            content=template_data.content or original_template.content,
            variables=self._serialize_variables(template_data.variables) if template_data.variables else original_template.variables,
            default_values=template_data.default_values or original_template.default_values,
            example_context=template_data.example_context or original_template.example_context,
            supported_providers=template_data.supported_providers or original_template.supported_providers,
            supported_models=template_data.supported_models or original_template.supported_models,
            use_cases=template_data.use_cases or original_template.use_cases,
            tags=template_data.tags or original_template.tags,
            visibility=template_data.visibility.value if template_data.visibility else original_template.visibility,
            owner_id=original_template.owner_id,
            team_id=template_data.team_id or original_template.team_id,
            version=new_version,
            parent_template_id=original_template.parent_template_id or original_template.id,
            is_latest_version=True,
            is_featured=original_template.is_featured,
            is_verified=False  # 新版本需要重新验证
        )
        
        db.add(new_template)
        await db.commit()
        await db.refresh(new_template)
        
        logger.info(f"Created new template version: {new_template.name} v{new_version} (ID: {new_template.id})")
        return new_template
    
    async def get_template_versions(self, db: AsyncSession, template_id: int, 
                                  user_id: Optional[int] = None) -> List[AIPromptTemplate]:
        """获取模板的所有版本"""
        # 获取原模板以确定版本链
        template = await self.get_template(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        # 找到根模板ID
        root_template_id = template.parent_template_id or template.id
        
        # 查询所有版本
        query = select(AIPromptTemplate).where(
            or_(
                AIPromptTemplate.id == root_template_id,
                AIPromptTemplate.parent_template_id == root_template_id
            )
        ).order_by(AIPromptTemplate.created_at)
        
        # 权限检查
        if user_id:
            query = query.where(
                or_(
                    AIPromptTemplate.owner_id == user_id,
                    AIPromptTemplate.visibility == TemplateVisibility.PUBLIC.value,
                    and_(
                        AIPromptTemplate.visibility == TemplateVisibility.TEAM.value,
                        AIPromptTemplate.team_id.isnot(None)
                    )
                )
            )
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_template_version_by_number(self, db: AsyncSession, template_id: int, 
                                           version: str, user_id: Optional[int] = None) -> Optional[AIPromptTemplate]:
        """根据版本号获取特定版本的模板"""
        versions = await self.get_template_versions(db, template_id, user_id)
        
        for template_version in versions:
            if template_version.version == version:
                return template_version
        
        return None
    
    async def get_latest_template_version(self, db: AsyncSession, template_id: int, 
                                        user_id: Optional[int] = None) -> Optional[AIPromptTemplate]:
        """获取模板的最新版本"""
        versions = await self.get_template_versions(db, template_id, user_id)
        
        for template_version in versions:
            if template_version.is_latest_version:
                return template_version
        
        # 如果没有标记为最新版本的，返回最后创建的
        return versions[-1] if versions else None
    
    async def rollback_to_version(self, db: AsyncSession, template_id: int, 
                                target_version: str, user_id: int) -> AIPromptTemplate:
        """回滚到指定版本"""
        # 获取目标版本
        target_template = await self.get_template_version_by_number(db, template_id, target_version, user_id)
        if not target_template:
            raise ValueError(f"版本 {target_version} 不存在")
        
        if target_template.owner_id != user_id:
            raise ValueError("只有模板所有者可以回滚版本")
        
        # 获取所有版本
        versions = await self.get_template_versions(db, template_id, user_id)
        
        # 将所有版本标记为非最新
        for version in versions:
            version.is_latest_version = False
        
        # 将目标版本标记为最新
        target_template.is_latest_version = True
        
        await db.commit()
        await db.refresh(target_template)
        
        logger.info(f"Rolled back template {template_id} to version {target_version}")
        return target_template
    
    async def compare_template_versions(self, db: AsyncSession, template_id: int, 
                                      version1: str, version2: str, 
                                      user_id: Optional[int] = None) -> Dict[str, Any]:
        """比较两个版本的差异"""
        template1 = await self.get_template_version_by_number(db, template_id, version1, user_id)
        template2 = await self.get_template_version_by_number(db, template_id, version2, user_id)
        
        if not template1 or not template2:
            raise ValueError("指定的版本不存在")
        
        # 比较各个字段
        differences = {
            "version1": version1,
            "version2": version2,
            "changes": {}
        }
        
        # 比较的字段列表
        compare_fields = [
            "title", "description", "content", "category", "subcategory",
            "variables", "default_values", "example_context", "supported_providers",
            "supported_models", "use_cases", "tags", "visibility"
        ]
        
        for field in compare_fields:
            value1 = getattr(template1, field)
            value2 = getattr(template2, field)
            
            if value1 != value2:
                differences["changes"][field] = {
                    "old_value": value1,
                    "new_value": value2,
                    "changed": True
                }
            else:
                differences["changes"][field] = {
                    "value": value1,
                    "changed": False
                }
        
        # 添加元数据
        differences["metadata"] = {
            "version1_created": template1.created_at.isoformat(),
            "version2_created": template2.created_at.isoformat(),
            "version1_usage": template1.usage_count,
            "version2_usage": template2.usage_count
        }
        
        return differences
    
    async def delete_template_version(self, db: AsyncSession, template_id: int, 
                                    version: str, user_id: int) -> bool:
        """删除特定版本（不能删除最新版本和唯一版本）"""
        target_template = await self.get_template_version_by_number(db, template_id, version, user_id)
        if not target_template:
            raise ValueError(f"版本 {version} 不存在")
        
        if target_template.owner_id != user_id:
            raise ValueError("只有模板所有者可以删除版本")
        
        # 检查是否是最新版本
        if target_template.is_latest_version:
            raise ValueError("不能删除最新版本")
        
        # 检查是否是唯一版本
        versions = await self.get_template_versions(db, template_id, user_id)
        if len(versions) <= 1:
            raise ValueError("不能删除唯一版本")
        
        await db.delete(target_template)
        await db.commit()
        
        logger.info(f"Deleted template version: {target_template.name} v{version}")
        return True
    
    async def get_template_version_history(self, db: AsyncSession, template_id: int, 
                                         user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取模板版本历史"""
        versions = await self.get_template_versions(db, template_id, user_id)
        
        history = []
        for i, version in enumerate(versions):
            # 计算与前一版本的差异
            changes_summary = []
            if i > 0:
                prev_version = versions[i-1]
                
                # 检查主要字段的变化
                if version.title != prev_version.title:
                    changes_summary.append("标题")
                if version.content != prev_version.content:
                    changes_summary.append("内容")
                if version.variables != prev_version.variables:
                    changes_summary.append("变量")
                if version.category != prev_version.category:
                    changes_summary.append("分类")
                if version.visibility != prev_version.visibility:
                    changes_summary.append("可见性")
            
            history.append({
                "version": version.version,
                "created_at": version.created_at.isoformat(),
                "is_latest": version.is_latest_version,
                "usage_count": version.usage_count,
                "rating_avg": version.rating_avg,
                "changes_summary": changes_summary,
                "template_id": version.id
            })
        
        return history
    
    async def _generate_next_version(self, db: AsyncSession, template_id: int) -> str:
        """生成下一个版本号"""
        versions = await self.get_template_versions(db, template_id)
        
        if not versions:
            return "1.0.0"
        
        # 获取最高版本号
        version_numbers = []
        for version in versions:
            try:
                parts = version.version.split('.')
                if len(parts) == 3:
                    major, minor, patch = map(int, parts)
                    version_numbers.append((major, minor, patch))
            except ValueError:
                continue
        
        if not version_numbers:
            return "1.0.0"
        
        # 找到最高版本并递增
        max_version = max(version_numbers)
        major, minor, patch = max_version
        
        # 默认递增patch版本
        return f"{major}.{minor}.{patch + 1}"
    
    async def set_template_as_latest(self, db: AsyncSession, template_id: int, 
                                   version: str, user_id: int) -> AIPromptTemplate:
        """将指定版本设置为最新版本"""
        target_template = await self.get_template_version_by_number(db, template_id, version, user_id)
        if not target_template:
            raise ValueError(f"版本 {version} 不存在")
        
        if target_template.owner_id != user_id:
            raise ValueError("只有模板所有者可以设置最新版本")
        
        # 获取所有版本并更新最新标记
        versions = await self.get_template_versions(db, template_id, user_id)
        for v in versions:
            v.is_latest_version = (v.id == target_template.id)
        
        await db.commit()
        await db.refresh(target_template)
        
        logger.info(f"Set template version {version} as latest for template {template_id}")
        return target_template    

    # ==================== 模板测试功能 ====================
    
    async def test_template(self, db: AsyncSession, template_id: int, 
                          test_request: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """测试提示词模板"""
        # 获取模板
        template = await self.get_template(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        # 解析测试请求
        test_context = test_request.get('context', {})
        ai_provider = test_request.get('ai_provider', 'openai')
        ai_model = test_request.get('ai_model', 'gpt-3.5-turbo')
        test_scenarios = test_request.get('test_scenarios', [])
        
        # 渲染模板
        variables = None
        if template.variables:
            variables = [TemplateVariable(**var) for var in template.variables]
        
        rendered_content, variables_used, missing_variables = await self.renderer.render(
            template.content, test_context, variables
        )
        
        # 检查缺失变量
        if missing_variables:
            return {
                "success": False,
                "error": f"缺少必需变量: {', '.join(missing_variables)}",
                "missing_variables": missing_variables,
                "template_id": template_id,
                "test_timestamp": datetime.utcnow().isoformat()
            }
        
        # 执行AI测试
        test_results = []
        
        if not test_scenarios:
            # 单次测试
            test_result = await self._execute_ai_test(
                rendered_content, ai_provider, ai_model, test_context
            )
            test_results.append(test_result)
        else:
            # 多场景测试
            for i, scenario in enumerate(test_scenarios):
                scenario_context = {**test_context, **scenario.get('context', {})}
                scenario_rendered, _, scenario_missing = await self.renderer.render(
                    template.content, scenario_context, variables
                )
                
                if scenario_missing:
                    test_results.append({
                        "scenario_index": i,
                        "scenario_name": scenario.get('name', f'场景 {i+1}'),
                        "success": False,
                        "error": f"缺少必需变量: {', '.join(scenario_missing)}",
                        "missing_variables": scenario_missing
                    })
                    continue
                
                test_result = await self._execute_ai_test(
                    scenario_rendered, 
                    scenario.get('ai_provider', ai_provider),
                    scenario.get('ai_model', ai_model),
                    scenario_context
                )
                test_result.update({
                    "scenario_index": i,
                    "scenario_name": scenario.get('name', f'场景 {i+1}'),
                    "expected_output": scenario.get('expected_output'),
                    "evaluation_criteria": scenario.get('evaluation_criteria')
                })
                test_results.append(test_result)
        
        # 计算总体测试结果
        successful_tests = sum(1 for result in test_results if result.get('success', False))
        total_tests = len(test_results)
        success_rate = successful_tests / total_tests if total_tests > 0 else 0
        
        # 保存测试记录
        test_record = {
            "template_id": template_id,
            "user_id": user_id,
            "test_context": test_context,
            "ai_provider": ai_provider,
            "ai_model": ai_model,
            "test_results": test_results,
            "success_rate": success_rate,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "test_timestamp": datetime.utcnow().isoformat()
        }
        
        await self._save_test_record(db, test_record)
        
        return {
            "success": True,
            "template_id": template_id,
            "template_name": template.name,
            "rendered_content": rendered_content,
            "variables_used": variables_used,
            "test_results": test_results,
            "success_rate": success_rate,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "test_timestamp": datetime.utcnow().isoformat(),
            "performance_metrics": await self._calculate_performance_metrics(test_results)
        }
    
    async def batch_test_template(self, db: AsyncSession, template_id: int,
                                batch_test_request: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """批量测试提示词模板"""
        template = await self.get_template(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        test_cases = batch_test_request.get('test_cases', [])
        ai_providers = batch_test_request.get('ai_providers', ['openai'])
        ai_models = batch_test_request.get('ai_models', ['gpt-3.5-turbo'])
        
        if not test_cases:
            raise ValueError("批量测试需要提供测试用例")
        
        batch_results = []
        
        # 对每个AI提供商和模型组合进行测试
        for provider in ai_providers:
            for model in ai_models:
                provider_model_results = []
                
                for i, test_case in enumerate(test_cases):
                    test_request = {
                        'context': test_case.get('context', {}),
                        'ai_provider': provider,
                        'ai_model': model,
                        'test_scenarios': [test_case] if 'scenarios' not in test_case else test_case['scenarios']
                    }
                    
                    try:
                        result = await self.test_template(db, template_id, test_request, user_id)
                        provider_model_results.append({
                            "test_case_index": i,
                            "test_case_name": test_case.get('name', f'测试用例 {i+1}'),
                            "result": result
                        })
                    except Exception as e:
                        provider_model_results.append({
                            "test_case_index": i,
                            "test_case_name": test_case.get('name', f'测试用例 {i+1}'),
                            "result": {
                                "success": False,
                                "error": str(e)
                            }
                        })
                
                # 计算该提供商+模型组合的统计信息
                successful_cases = sum(1 for r in provider_model_results 
                                     if r['result'].get('success', False))
                total_cases = len(provider_model_results)
                
                batch_results.append({
                    "ai_provider": provider,
                    "ai_model": model,
                    "test_results": provider_model_results,
                    "success_rate": successful_cases / total_cases if total_cases > 0 else 0,
                    "total_cases": total_cases,
                    "successful_cases": successful_cases
                })
        
        # 计算总体统计
        total_success_rate = sum(r['success_rate'] for r in batch_results) / len(batch_results) if batch_results else 0
        
        return {
            "success": True,
            "template_id": template_id,
            "template_name": template.name,
            "batch_results": batch_results,
            "overall_success_rate": total_success_rate,
            "total_provider_model_combinations": len(batch_results),
            "total_test_cases": len(test_cases),
            "test_timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_template_test_history(self, db: AsyncSession, template_id: int,
                                      user_id: int, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取模板测试历史"""
        template = await self.get_template(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        # 这里应该从数据库查询测试历史记录
        # 由于当前没有测试历史表，我们返回模拟数据
        # 在实际实现中，需要创建相应的数据库表和模型
        
        return {
            "template_id": template_id,
            "template_name": template.name,
            "test_history": [],
            "total": 0,
            "page": page,
            "size": size,
            "pages": 0
        }
    
    async def evaluate_template_performance(self, db: AsyncSession, template_id: int,
                                          evaluation_request: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """评估模板性能"""
        template = await self.get_template(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        evaluation_criteria = evaluation_request.get('criteria', [])
        test_data = evaluation_request.get('test_data', [])
        
        if not test_data:
            raise ValueError("性能评估需要提供测试数据")
        
        # 执行性能测试
        performance_results = []
        
        for i, data in enumerate(test_data):
            test_request = {
                'context': data.get('context', {}),
                'ai_provider': data.get('ai_provider', 'openai'),
                'ai_model': data.get('ai_model', 'gpt-3.5-turbo')
            }
            
            start_time = datetime.utcnow()
            result = await self.test_template(db, template_id, test_request, user_id)
            end_time = datetime.utcnow()
            
            response_time = (end_time - start_time).total_seconds()
            
            performance_results.append({
                "test_index": i,
                "response_time": response_time,
                "success": result.get('success', False),
                "token_usage": result.get('token_usage', 0),
                "result": result
            })
        
        # 计算性能指标
        response_times = [r['response_time'] for r in performance_results]
        success_count = sum(1 for r in performance_results if r['success'])
        
        performance_metrics = {
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "success_rate": success_count / len(performance_results) if performance_results else 0,
            "total_tests": len(performance_results),
            "successful_tests": success_count
        }
        
        return {
            "success": True,
            "template_id": template_id,
            "template_name": template.name,
            "performance_results": performance_results,
            "performance_metrics": performance_metrics,
            "evaluation_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _execute_ai_test(self, prompt: str, ai_provider: str, ai_model: str, 
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """执行AI测试"""
        try:
            # 模拟AI调用 - 在实际实现中，这里应该调用真实的AI服务
            # 这里返回模拟结果
            import time
            import random
            
            # 模拟响应时间
            response_time = random.uniform(0.5, 3.0)
            await asyncio.sleep(0.1)  # 模拟网络延迟
            
            # 模拟AI响应
            ai_response = f"这是使用 {ai_provider} 的 {ai_model} 模型对提示词的响应。\n\n提示词内容: {prompt[:100]}..."
            
            # 模拟token使用量
            token_usage = len(prompt.split()) + len(ai_response.split())
            
            return {
                "success": True,
                "ai_provider": ai_provider,
                "ai_model": ai_model,
                "prompt": prompt,
                "response": ai_response,
                "response_time": response_time,
                "token_usage": token_usage,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "ai_provider": ai_provider,
                "ai_model": ai_model,
                "prompt": prompt,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _calculate_performance_metrics(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算性能指标"""
        if not test_results:
            return {}
        
        response_times = [r.get('response_time', 0) for r in test_results if r.get('response_time')]
        token_usages = [r.get('token_usage', 0) for r in test_results if r.get('token_usage')]
        
        return {
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "total_token_usage": sum(token_usages),
            "avg_token_usage": sum(token_usages) / len(token_usages) if token_usages else 0
        }
    
    async def _save_test_record(self, db: AsyncSession, test_record: Dict[str, Any]) -> None:
        """保存测试记录"""
        # 在实际实现中，这里应该保存到数据库
        # 目前只是记录日志
        logger.info(f"Template test completed: template_id={test_record['template_id']}, "
                   f"success_rate={test_record['success_rate']}")
        pass