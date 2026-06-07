"""
团队管理API接口

本模块提供团队管理的REST API接口，包括：
- 团队成员CRUD操作
- 成员邀请功能
- 工作负载分析
- 技能匹配推荐
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, NotFoundError, PermissionError
from ...services.team_service import TeamService, get_team_service
from ...api.auth import get_current_user
from ...models.user import User
from ...schemas.team import (
    AddMemberRequest, UpdateMemberRequest, InviteMemberRequest,
    MemberQueryParams, ProjectMemberResponse, MemberListResponse,
    AddMemberResponse, UpdateMemberResponse, RemoveMemberResponse,
    InviteMemberResponse, TeamWorkloadAnalysis, SkillMatchRequest,
    SkillMatchResponse, TeamStatistics, ProjectMemberRole, MemberStatus,
    UserInfo
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/projects/{project_id}/members",
    response_model=AddMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="添加团队成员",
    description="向项目添加新的团队成员，包含角色分配和权限验证"
)
async def add_team_member(
    project_id: int = Path(..., description="项目ID"),
    request: AddMemberRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    添加团队成员
    
    - **user_id**: 用户ID（必填）
    - **role_in_project**: 项目内角色（必填）
    - **allocation_percentage**: 参与度百分比（0-100，默认100）
    - **hourly_rate**: 小时费率（可选）
    - **join_date**: 加入日期（必填，不能是未来日期）
    - **skills**: 技能标签列表（可选）
    - **responsibilities**: 职责描述（可选）
    
    权限要求：
    - 需要项目管理权限
    - 被添加的用户必须存在且状态正常
    - 用户不能已经是项目成员
    """
    try:
        team_service = get_team_service(db)
        member = await team_service.add_team_member(project_id, request, current_user.id)
        
        # 获取用户信息用于响应
        user_info = UserInfo(
            id=member.user_id,
            username="",  # 需要从数据库获取
            email="",
            nickname="",
            avatar=None,
            phone=None
        )
        
        member_response = ProjectMemberResponse(
            id=member.id,
            project_id=member.project_id,
            user_id=member.user_id,
            user_info=user_info,
            role_in_project=ProjectMemberRole(member.role_in_project),
            allocation_percentage=member.allocation_percentage,
            hourly_rate=member.hourly_rate,
            join_date=member.join_date,
            leave_date=member.leave_date,
            status=MemberStatus(member.status),
            skills=member.skills,
            responsibilities=member.responsibilities,
            created_at=member.created_at,
            updated_at=member.updated_at
        )
        
        return AddMemberResponse(
            success=True,
            message="团队成员添加成功",
            member=member_response
        )
        
    except ValidationError as e:
        logger.warning(f"添加团队成员数据验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"添加团队成员权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except NotFoundError as e:
        logger.warning(f"添加团队成员失败，资源不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"添加团队成员失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="添加团队成员失败，请稍后重试"
        )


@router.get(
    "/projects/{project_id}/members",
    response_model=MemberListResponse,
    summary="获取团队成员列表",
    description="获取项目的团队成员列表，支持分页、过滤、搜索和排序"
)
async def get_team_members(
    project_id: int = Path(..., description="项目ID"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    role: Optional[List[ProjectMemberRole]] = Query(None, description="角色过滤"),
    status: Optional[List[MemberStatus]] = Query(None, description="状态过滤"),
    skills: Optional[List[str]] = Query(None, description="技能过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: Optional[str] = Query("join_date", description="排序字段"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取团队成员列表
    
    支持的功能：
    - **分页**: 通过page和size参数控制
    - **角色过滤**: 可选择多个项目角色
    - **状态过滤**: 可选择多个成员状态
    - **技能过滤**: 按技能标签筛选
    - **关键词搜索**: 在用户名、邮箱、昵称、职责中搜索
    - **排序**: 支持多字段排序，升序或降序
    - **权限控制**: 根据用户权限返回可访问的成员信息
    """
    try:
        # 构建查询参数
        params = MemberQueryParams(
            page=page,
            size=size,
            role=role,
            status=status,
            skills=skills,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        team_service = get_team_service(db)
        members, total = await team_service.get_team_members(project_id, params, current_user.id)
        
        # 转换为响应格式
        member_responses = []
        for member in members:
            user_info = UserInfo(
                id=member.user_id,
                username="",  # 需要从数据库获取
                email="",
                nickname="",
                avatar=None,
                phone=None
            )
            
            member_response = ProjectMemberResponse(
                id=member.id,
                project_id=member.project_id,
                user_id=member.user_id,
                user_info=user_info,
                role_in_project=ProjectMemberRole(member.role_in_project),
                allocation_percentage=member.allocation_percentage,
                hourly_rate=member.hourly_rate,
                join_date=member.join_date,
                leave_date=member.leave_date,
                status=MemberStatus(member.status),
                skills=member.skills,
                responsibilities=member.responsibilities,
                created_at=member.created_at,
                updated_at=member.updated_at
            )
            member_responses.append(member_response)
        
        # 计算总页数
        total_pages = (total + size - 1) // size
        
        return MemberListResponse(
            members=member_responses,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
        
    except PermissionError as e:
        logger.warning(f"获取团队成员列表权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except NotFoundError as e:
        logger.warning(f"获取团队成员列表失败，项目不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取团队成员列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取团队成员列表失败，请稍后重试"
        )


@router.put(
    "/projects/{project_id}/members/{member_id}",
    response_model=UpdateMemberResponse,
    summary="更新团队成员信息",
    description="更新团队成员的角色、分配比例、状态等信息"
)
async def update_team_member(
    project_id: int = Path(..., description="项目ID"),
    member_id: int = Path(..., description="成员ID"),
    request: UpdateMemberRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    更新团队成员信息
    
    支持更新的字段：
    - **role_in_project**: 项目内角色
    - **allocation_percentage**: 参与度百分比
    - **hourly_rate**: 小时费率
    - **leave_date**: 离开日期（设置后会自动更新状态）
    - **status**: 成员状态
    - **skills**: 技能标签
    - **responsibilities**: 职责描述
    
    注意：
    - 只能更新提供的字段，未提供的字段保持不变
    - 角色变更需要相应权限
    - 设置离开日期会自动调整成员状态
    """
    try:
        team_service = get_team_service(db)
        member = await team_service.update_team_member(
            project_id, member_id, request, current_user.id
        )
        
        # 构建响应
        user_info = UserInfo(
            id=member.user_id,
            username="",
            email="",
            nickname="",
            avatar=None,
            phone=None
        )
        
        member_response = ProjectMemberResponse(
            id=member.id,
            project_id=member.project_id,
            user_id=member.user_id,
            user_info=user_info,
            role_in_project=ProjectMemberRole(member.role_in_project),
            allocation_percentage=member.allocation_percentage,
            hourly_rate=member.hourly_rate,
            join_date=member.join_date,
            leave_date=member.leave_date,
            status=MemberStatus(member.status),
            skills=member.skills,
            responsibilities=member.responsibilities,
            created_at=member.created_at,
            updated_at=member.updated_at
        )
        
        return UpdateMemberResponse(
            success=True,
            message="团队成员信息更新成功",
            member=member_response
        )
        
    except NotFoundError as e:
        logger.warning(f"更新团队成员失败，成员不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"更新团队成员数据验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"更新团队成员权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新团队成员失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新团队成员失败，请稍后重试"
        )


@router.delete(
    "/projects/{project_id}/members/{member_id}",
    response_model=RemoveMemberResponse,
    summary="移除团队成员",
    description="从项目中移除团队成员"
)
async def remove_team_member(
    project_id: int = Path(..., description="项目ID"),
    member_id: int = Path(..., description="成员ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    移除团队成员
    
    执行成员移除操作：
    - 从项目团队中移除指定成员
    - 检查移除条件（如项目经理等关键角色）
    - 发送移除通知
    - 处理相关任务和权限
    
    限制条件：
    - 需要团队管理权限
    - 某些关键角色可能不能被移除
    - 可能需要处理成员的未完成任务
    """
    try:
        team_service = get_team_service(db)
        success = await team_service.remove_team_member(project_id, member_id, current_user.id)
        
        if success:
            return RemoveMemberResponse(
                success=True,
                message="团队成员移除成功",
                member_id=member_id,
                removed_at=datetime.utcnow()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="团队成员移除失败"
            )
        
    except NotFoundError as e:
        logger.warning(f"移除团队成员失败，成员不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"移除团队成员验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"移除团队成员权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"移除团队成员失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="移除团队成员失败，请稍后重试"
        )


@router.post(
    "/projects/{project_id}/members/invite",
    response_model=InviteMemberResponse,
    summary="邀请成员加入项目",
    description="通过邮箱邀请新成员加入项目团队"
)
async def invite_member_by_email(
    project_id: int = Path(..., description="项目ID"),
    request: InviteMemberRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    邀请成员加入项目
    
    - **email**: 邀请邮箱地址（必填）
    - **role_in_project**: 项目内角色（必填）
    - **allocation_percentage**: 参与度百分比（默认100）
    - **hourly_rate**: 小时费率（可选）
    - **skills**: 技能标签（可选）
    - **responsibilities**: 职责描述（可选）
    - **invitation_message**: 邀请消息（可选）
    
    处理逻辑：
    - 如果邮箱对应的用户已存在，直接添加到项目
    - 如果用户不存在，发送邀请邮件
    - 邀请链接有效期为7天
    - 发送邮件通知被邀请人
    """
    try:
        team_service = get_team_service(db)
        result = await team_service.invite_member_by_email(project_id, request, current_user.id)
        
        return InviteMemberResponse(
            success=True,
            message="邀请发送成功" if not result["user_exists"] else "用户已直接添加到项目",
            invitation_id=result["invitation_id"],
            invited_email=result["invited_email"],
            expires_at=result["expires_at"]
        )
        
    except ValidationError as e:
        logger.warning(f"邀请成员数据验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"邀请成员权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except NotFoundError as e:
        logger.warning(f"邀请成员失败，项目不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"邀请成员失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="邀请成员失败，请稍后重试"
        )


@router.get(
    "/projects/{project_id}/members/workload",
    response_model=TeamWorkloadAnalysis,
    summary="获取团队工作负载分析",
    description="分析团队成员的工作负载分布和利用率"
)
async def get_team_workload_analysis(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取团队工作负载分析
    
    返回团队工作负载的详细分析，包括：
    - 团队整体工作负载和利用率
    - 每个成员的工作负载详情
    - 识别过载和负载不足的成员
    - 工作负载平衡建议
    
    分析维度：
    - 当前项目参与度
    - 跨项目工作负载
    - 可用容量分析
    - 负载均衡建议
    """
    try:
        team_service = get_team_service(db)
        analysis = await team_service.get_team_workload_analysis(project_id, current_user.id)
        
        return analysis
        
    except PermissionError as e:
        logger.warning(f"获取团队工作负载分析权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except NotFoundError as e:
        logger.warning(f"获取团队工作负载分析失败，项目不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取团队工作负载分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取团队工作负载分析失败，请稍后重试"
        )


@router.post(
    "/projects/{project_id}/members/recommend",
    response_model=SkillMatchResponse,
    summary="推荐团队成员",
    description="基于技能匹配和工作负载分析推荐合适的团队成员"
)
async def recommend_team_members(
    project_id: int = Path(..., description="项目ID"),
    request: SkillMatchRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    推荐团队成员
    
    基于以下因素进行智能推荐：
    - **技能匹配度**: 候选人技能与需求的匹配程度
    - **工作负载**: 候选人当前的工作负载情况
    - **历史绩效**: 候选人的历史工作表现
    - **可用性**: 候选人的时间可用性
    
    推荐参数：
    - **skill_requirements**: 技能需求列表（必填）
    - **max_recommendations**: 最大推荐数量（1-50，默认10）
    - **include_current_members**: 是否包含当前成员（默认false）
    - **min_score_threshold**: 最低评分阈值（0-1，默认0.6）
    
    返回按综合评分排序的推荐列表。
    """
    try:
        team_service = get_team_service(db)
        recommendations = await team_service.recommend_team_members(
            project_id, request, current_user.id
        )
        
        return SkillMatchResponse(
            success=True,
            message=f"找到 {len(recommendations)} 个推荐候选人",
            recommendations=recommendations,
            total_candidates=len(recommendations),
            match_criteria=request
        )
        
    except ValidationError as e:
        logger.warning(f"推荐团队成员数据验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"推荐团队成员权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except NotFoundError as e:
        logger.warning(f"推荐团队成员失败，项目不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"推荐团队成员失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="推荐团队成员失败，请稍后重试"
        )


@router.get(
    "/projects/{project_id}/members/statistics",
    response_model=TeamStatistics,
    summary="获取团队统计信息",
    description="获取项目团队的统计信息和分析数据"
)
async def get_team_statistics(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取团队统计信息
    
    返回团队的详细统计数据，包括：
    - 团队规模和成员分布
    - 角色和状态统计
    - 技能分布分析
    - 成本和工时统计
    - 经验分布情况
    
    适用于：
    - 团队管理决策
    - 资源规划
    - 绩效分析
    - 报告生成
    """
    try:
        team_service = get_team_service(db)
        statistics = await team_service.get_team_statistics(project_id, current_user.id)
        
        return statistics
        
    except PermissionError as e:
        logger.warning(f"获取团队统计信息权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except NotFoundError as e:
        logger.warning(f"获取团队统计信息失败，项目不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取团队统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取团队统计信息失败，请稍后重试"
        )