"""
提示词模板管理API端点

提供提示词模板的完整REST API，包括：
1. 模板的CRUD操作
2. 模板搜索和筛选
3. 模板渲染
4. 使用统计和评分
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.auth import get_current_user
from ...models.user import User
from ...services.prompt_service import PromptService
from ...schemas.prompt_template import (
    PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateResponse,
    PromptTemplateListResponse, TemplateRenderRequest, TemplateRenderResponse,
    TemplateUsageCreate, TemplateUsageResponse, TemplateSearchRequest,
    TemplateStatistics, TemplateCategory, TemplateVisibility
)

router = APIRouter()
prompt_service = PromptService()


@router.post("/", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建提示词模板"""
    try:
        template = await prompt_service.create_template(db, template_data, current_user.id)
        return PromptTemplateResponse.from_orm(template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建模板失败")


@router.get("/{template_id}", response_model=PromptTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """获取单个提示词模板"""
    user_id = current_user.id if current_user else None
    template = await prompt_service.get_template(db, template_id, user_id)
    
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在或无权限访问")
    
    return PromptTemplateResponse.from_orm(template)


@router.put("/{template_id}", response_model=PromptTemplateResponse)
async def update_template(
    template_id: int,
    template_data: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新提示词模板"""
    try:
        template = await prompt_service.update_template(db, template_id, template_data, current_user.id)
        return PromptTemplateResponse.from_orm(template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新模板失败")


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除提示词模板"""
    try:
        await prompt_service.delete_template(db, template_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除模板失败")


@router.post("/search", response_model=PromptTemplateListResponse)
async def search_templates(
    search_request: TemplateSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """搜索提示词模板"""
    try:
        user_id = current_user.id if current_user else None
        return await prompt_service.search_templates(db, search_request, user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="搜索模板失败")


@router.get("/", response_model=PromptTemplateListResponse)
async def list_templates(
    category: Optional[TemplateCategory] = Query(None, description="分类筛选"),
    visibility: Optional[TemplateVisibility] = Query(None, description="可见性筛选"),
    is_featured: Optional[bool] = Query(None, description="是否精选"),
    is_verified: Optional[bool] = Query(None, description="是否已验证"),
    query: Optional[str] = Query(None, description="搜索关键词", max_length=200),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向", pattern="^(asc|desc)$"),
    page: int = Query(1, description="页码", ge=1),
    size: int = Query(20, description="每页大小", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """获取提示词模板列表"""
    try:
        search_request = TemplateSearchRequest(
            query=query,
            category=category,
            visibility=visibility,
            is_featured=is_featured,
            is_verified=is_verified,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            size=size
        )
        
        user_id = current_user.id if current_user else None
        return await prompt_service.search_templates(db, search_request, user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取模板列表失败")


@router.post("/{template_id}/render", response_model=TemplateRenderResponse)
async def render_template(
    template_id: int,
    render_request: TemplateRenderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """渲染提示词模板"""
    try:
        if render_request.template_id != template_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模板ID不匹配")
        
        user_id = current_user.id if current_user else None
        return await prompt_service.render_template(db, template_id, render_request.context, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="渲染模板失败")


@router.post("/{template_id}/usage", response_model=TemplateUsageResponse, status_code=status.HTTP_201_CREATED)
async def record_template_usage(
    template_id: int,
    usage_data: TemplateUsageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """记录模板使用情况"""
    try:
        if usage_data.template_id != template_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模板ID不匹配")
        
        usage = await prompt_service.record_template_usage(db, usage_data, current_user.id)
        return TemplateUsageResponse.from_orm(usage)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="记录使用情况失败")


@router.get("/statistics/overview", response_model=TemplateStatistics)
async def get_template_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """获取模板统计信息"""
    try:
        user_id = current_user.id if current_user else None
        return await prompt_service.get_template_statistics(db, user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取统计信息失败")


@router.get("/user/my-templates", response_model=PromptTemplateListResponse)
async def get_my_templates(
    category: Optional[str] = Query(None, description="分类筛选"),
    include_public: bool = Query(True, description="是否包含公开模板"),
    page: int = Query(1, description="页码", ge=1),
    size: int = Query(20, description="每页大小", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的提示词模板"""
    try:
        return await prompt_service.get_user_templates(
            db, current_user.id, category, include_public, page, size
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取用户模板失败")


@router.get("/categories", response_model=List[dict])
async def get_template_categories():
    """获取模板分类列表"""
    categories = [
        {"value": "GENERAL", "label": "通用对话", "description": "日常交流、问答咨询"},
        {"value": "CODE_GENERATION", "label": "代码编程", "description": "代码生成、调试、优化"},
        {"value": "TEST_CASE", "label": "测试相关", "description": "测试用例、测试策略"},
        {"value": "DOCUMENT_WRITING", "label": "文档写作", "description": "技术文档、报告撰写"},
        {"value": "DATA_ANALYSIS", "label": "数据分析", "description": "数据处理、统计分析"},
        {"value": "CREATIVE_WRITING", "label": "创意设计", "description": "方案设计、创意思考"},
        {"value": "LEARNING_EDUCATION", "label": "学习教育", "description": "知识学习、技能培训"},
        {"value": "PROJECT_MANAGEMENT", "label": "项目管理", "description": "项目规划、风险管理"}
    ]
    return categories


@router.get("/visibility-options", response_model=List[dict])
async def get_visibility_options():
    """获取可见性选项"""
    options = [
        {"value": "PRIVATE", "label": "私有", "description": "仅自己可见"},
        {"value": "TEAM", "label": "团队", "description": "团队成员可见"},
        {"value": "PUBLIC", "label": "公开", "description": "所有人可见"}
    ]
    return options


# ==================== 版本管理API端点 ====================

@router.post("/{template_id}/versions", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template_version(
    template_id: int,
    template_data: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建模板新版本"""
    try:
        template = await prompt_service.create_template_version(db, template_id, template_data, current_user.id)
        return PromptTemplateResponse.from_orm(template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建新版本失败")


@router.get("/{template_id}/versions", response_model=List[PromptTemplateResponse])
async def get_template_versions(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """获取模板的所有版本"""
    try:
        user_id = current_user.id if current_user else None
        versions = await prompt_service.get_template_versions(db, template_id, user_id)
        return [PromptTemplateResponse.from_orm(version) for version in versions]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取版本列表失败")


@router.get("/{template_id}/versions/{version}", response_model=PromptTemplateResponse)
async def get_template_version_by_number(
    template_id: int,
    version: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """根据版本号获取特定版本的模板"""
    try:
        user_id = current_user.id if current_user else None
        template = await prompt_service.get_template_version_by_number(db, template_id, version, user_id)
        
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"版本 {version} 不存在")
        
        return PromptTemplateResponse.from_orm(template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取指定版本失败")


@router.get("/{template_id}/versions/latest", response_model=PromptTemplateResponse)
async def get_latest_template_version(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """获取模板的最新版本"""
    try:
        user_id = current_user.id if current_user else None
        template = await prompt_service.get_latest_template_version(db, template_id, user_id)
        
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在或无权限访问")
        
        return PromptTemplateResponse.from_orm(template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取最新版本失败")


@router.post("/{template_id}/versions/{version}/rollback", response_model=PromptTemplateResponse)
async def rollback_to_version(
    template_id: int,
    version: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """回滚到指定版本"""
    try:
        template = await prompt_service.rollback_to_version(db, template_id, version, current_user.id)
        return PromptTemplateResponse.from_orm(template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="版本回滚失败")


@router.get("/{template_id}/versions/compare/{version1}/{version2}")
async def compare_template_versions(
    template_id: int,
    version1: str,
    version2: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """比较两个版本的差异"""
    try:
        user_id = current_user.id if current_user else None
        comparison = await prompt_service.compare_template_versions(db, template_id, version1, version2, user_id)
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="版本比较失败")


@router.delete("/{template_id}/versions/{version}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template_version(
    template_id: int,
    version: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除特定版本（不能删除最新版本和唯一版本）"""
    try:
        await prompt_service.delete_template_version(db, template_id, version, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除版本失败")


@router.get("/{template_id}/versions/history")
async def get_template_version_history(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """获取模板版本历史"""
    try:
        user_id = current_user.id if current_user else None
        history = await prompt_service.get_template_version_history(db, template_id, user_id)
        return {"template_id": template_id, "history": history}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取版本历史失败")


@router.post("/{template_id}/versions/{version}/set-latest", response_model=PromptTemplateResponse)
async def set_template_as_latest(
    template_id: int,
    version: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """将指定版本设置为最新版本"""
    try:
        template = await prompt_service.set_template_as_latest(db, template_id, version, current_user.id)
        return PromptTemplateResponse.from_orm(template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="设置最新版本失败")


# ==================== 模板测试API端点 ====================

@router.post("/{template_id}/test", response_model=dict)
async def test_template(
    template_id: int,
    test_request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """测试提示词模板"""
    try:
        result = await prompt_service.test_template(
            db, template_id, test_request, current_user.id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="模板测试失败")


@router.post("/{template_id}/test/batch", response_model=dict)
async def batch_test_template(
    template_id: int,
    batch_test_request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量测试提示词模板"""
    try:
        result = await prompt_service.batch_test_template(
            db, template_id, batch_test_request, current_user.id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="批量测试失败")


@router.get("/{template_id}/test/history", response_model=dict)
async def get_template_test_history(
    template_id: int,
    page: int = Query(1, description="页码", ge=1),
    size: int = Query(20, description="每页大小", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取模板测试历史"""
    try:
        result = await prompt_service.get_template_test_history(
            db, template_id, current_user.id, page, size
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取测试历史失败")


@router.post("/{template_id}/test/evaluate", response_model=dict)
async def evaluate_template_performance(
    template_id: int,
    evaluation_request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """评估模板性能"""
    try:
        result = await prompt_service.evaluate_template_performance(
            db, template_id, evaluation_request, current_user.id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="模板评估失败")