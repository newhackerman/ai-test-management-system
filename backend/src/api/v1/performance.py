"""
性能监控API接口

本模块提供数据库和应用性能监控的REST API接口，包括：
- 慢查询分析
- 索引使用统计
- 缓存统计
- 性能优化建议
- Lighthouse Web性能分析
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...api.auth import get_current_user
from ...models.user import User
from ...utils.database_optimization import get_database_optimizer, query_monitor
from ...services.project_cache_service import project_cache_service
from ...core.lighthouse_manager import get_lighthouse_manager, LighthouseConfig

logger = logging.getLogger(__name__)

router = APIRouter()


class LighthouseAuditRequest(BaseModel):
    """Lighthouse审计请求"""
    url: str
    mobile: bool = False
    throttling: bool = True
    categories: Optional[List[str]] = None


class PerformanceComparisonRequest(BaseModel):
    """性能对比请求"""
    url: str
    baseline_date: datetime
    comparison_date: Optional[datetime] = None


@router.get(
    "/performance/slow-queries",
    summary="获取慢查询分析",
    description="分析系统中的慢查询，帮助识别性能瓶颈"
)
async def get_slow_queries(
    limit: int = Query(50, ge=1, le=100, description="返回的慢查询数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取慢查询分析
    
    返回系统中执行时间较长的查询，包括：
    - 查询SQL文本
    - 执行次数
    - 平均执行时间
    - 总执行时间
    - 扫描行数
    - 返回行数
    - 查询效率
    """
    try:
        # 检查用户权限（只有管理员可以查看性能数据）
        if current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看性能监控数据"
            )
        
        optimizer = await get_database_optimizer(db)
        slow_queries = await optimizer.analyze_slow_queries(limit)
        
        return {
            "success": True,
            "data": {
                "slow_queries": slow_queries,
                "total_count": len(slow_queries),
                "analysis_time": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取慢查询分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取慢查询分析失败"
        )


@router.get(
    "/performance/index-usage",
    summary="获取索引使用统计",
    description="分析数据库索引的使用情况，帮助优化索引策略"
)
async def get_index_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取索引使用统计
    
    返回数据库索引的使用情况，包括：
    - 索引名称
    - 表名
    - 列名
    - 读取次数
    - 插入次数
    - 更新次数
    - 删除次数
    - 总操作次数
    """
    try:
        # 检查用户权限
        if current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看性能监控数据"
            )
        
        optimizer = await get_database_optimizer(db)
        index_stats = await optimizer.analyze_index_usage()
        
        # 按使用频率排序
        index_stats.sort(key=lambda x: x['total_operations'], reverse=True)
        
        # 统计汇总信息
        total_indexes = len(index_stats)
        active_indexes = len([idx for idx in index_stats if idx['total_operations'] > 0])
        unused_indexes = total_indexes - active_indexes
        
        return {
            "success": True,
            "data": {
                "index_statistics": index_stats,
                "summary": {
                    "total_indexes": total_indexes,
                    "active_indexes": active_indexes,
                    "unused_indexes": unused_indexes,
                    "usage_rate": active_indexes / total_indexes if total_indexes > 0 else 0
                },
                "analysis_time": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取索引使用统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取索引使用统计失败"
        )


@router.get(
    "/performance/table-statistics",
    summary="获取表统计信息",
    description="获取数据库表的统计信息，包括行数、大小等"
)
async def get_table_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取表统计信息
    
    返回数据库表的统计信息，包括：
    - 表行数
    - 平均行长度
    - 数据大小
    - 索引大小
    - 碎片空间
    - 总大小
    """
    try:
        # 检查用户权限
        if current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看性能监控数据"
            )
        
        optimizer = await get_database_optimizer(db)
        table_stats = await optimizer.optimize_table_statistics()
        
        # 计算总计信息
        total_rows = sum(stats['rows'] for stats in table_stats.values())
        total_data_size = sum(stats['data_length'] for stats in table_stats.values())
        total_index_size = sum(stats['index_length'] for stats in table_stats.values())
        total_size = total_data_size + total_index_size
        
        return {
            "success": True,
            "data": {
                "table_statistics": table_stats,
                "summary": {
                    "total_tables": len(table_stats),
                    "total_rows": total_rows,
                    "total_data_size": total_data_size,
                    "total_index_size": total_index_size,
                    "total_size": total_size,
                    "index_ratio": total_index_size / total_size if total_size > 0 else 0
                },
                "analysis_time": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取表统计信息失败"
        )


@router.get(
    "/performance/query-statistics",
    summary="获取查询统计信息",
    description="获取应用层查询的性能统计信息"
)
async def get_query_statistics(
    query_name: Optional[str] = Query(None, description="特定查询名称"),
    current_user: User = Depends(get_current_user)
):
    """
    获取查询统计信息
    
    返回应用层查询的性能统计，包括：
    - 查询名称
    - 总执行次数
    - 成功次数
    - 失败次数
    - 总执行时间
    - 平均执行时间
    - 最大执行时间
    - 最小执行时间
    - 成功率
    """
    try:
        # 检查用户权限
        if current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看性能监控数据"
            )
        
        if query_name:
            # 获取特定查询的统计信息
            stats = await query_monitor.get_query_stats(query_name)
            return {
                "success": True,
                "data": {
                    "query_statistics": stats,
                    "analysis_time": datetime.utcnow().isoformat()
                }
            }
        else:
            # 获取所有查询的统计信息
            # 这里需要扩展query_monitor来支持获取所有查询统计
            return {
                "success": True,
                "data": {
                    "message": "请指定query_name参数获取特定查询统计",
                    "available_queries": [
                        "get_projects_list_optimized",
                        "get_project_with_details",
                        "get_project_statistics"
                    ],
                    "analysis_time": datetime.utcnow().isoformat()
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取查询统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取查询统计信息失败"
        )


@router.get(
    "/performance/cache-statistics",
    summary="获取缓存统计信息",
    description="获取Redis缓存的使用统计信息"
)
async def get_cache_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    获取缓存统计信息
    
    返回Redis缓存的统计信息，包括：
    - 各类缓存数量
    - 内存使用情况
    - 缓存命中率等
    """
    try:
        # 检查用户权限
        if current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看性能监控数据"
            )
        
        cache_stats = await project_cache_service.get_cache_statistics()
        
        return {
            "success": True,
            "data": {
                "cache_statistics": cache_stats,
                "analysis_time": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取缓存统计信息失败"
        )


@router.post(
    "/performance/optimize-indexes",
    summary="创建优化索引",
    description="创建数据库性能优化索引"
)
async def optimize_indexes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    创建优化索引
    
    为项目管理相关表创建性能优化索引，包括：
    - 复合索引
    - 覆盖索引
    - 全文索引
    """
    try:
        # 检查用户权限
        if current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以执行性能优化操作"
            )
        
        optimizer = await get_database_optimizer(db)
        created_indexes = await optimizer.create_optimized_indexes()
        
        return {
            "success": True,
            "data": {
                "created_indexes": created_indexes,
                "total_created": len(created_indexes),
                "optimization_time": datetime.utcnow().isoformat()
            },
            "message": f"成功创建 {len(created_indexes)} 个优化索引"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建优化索引失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建优化索引失败"
        )


@router.post(
    "/performance/clear-cache",
    summary="清除缓存",
    description="清除项目相关的缓存数据"
)
async def clear_cache(
    cache_type: str = Query("all", description="缓存类型: all, project, user, list"),
    target_id: Optional[int] = Query(None, description="目标ID（项目ID或用户ID）"),
    current_user: User = Depends(get_current_user)
):
    """
    清除缓存
    
    支持清除不同类型的缓存：
    - all: 清除所有项目相关缓存
    - project: 清除特定项目缓存（需要target_id）
    - user: 清除特定用户缓存（需要target_id）
    - list: 清除项目列表缓存
    """
    try:
        # 检查用户权限
        if current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以执行缓存清除操作"
            )
        
        deleted_count = 0
        
        if cache_type == "all":
            deleted_count = await project_cache_service.invalidate_all_project_caches()
        elif cache_type == "project":
            if not target_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="清除项目缓存需要提供target_id"
                )
            deleted_count = await project_cache_service.invalidate_project_cache(target_id)
        elif cache_type == "user":
            if not target_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="清除用户缓存需要提供target_id"
                )
            deleted_count = await project_cache_service.invalidate_user_cache(target_id)
        elif cache_type == "list":
            deleted_count = await project_cache_service.redis.delete(*await project_cache_service.redis.keys("projects_list:*"))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不支持的缓存类型"
            )
        
        return {
            "success": True,
            "data": {
                "cache_type": cache_type,
                "target_id": target_id,
                "deleted_count": deleted_count,
                "clear_time": datetime.utcnow().isoformat()
            },
            "message": f"成功清除 {deleted_count} 个缓存项"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清除缓存失败"
        )


@router.post(
    "/performance/warmup-cache",
    summary="预热缓存",
    description="预热项目相关缓存数据"
)
async def warmup_cache(
    project_ids: List[int] = Query(..., description="要预热的项目ID列表"),
    current_user: User = Depends(get_current_user)
):
    """
    预热缓存
    
    为指定的项目预热缓存数据，包括：
    - 项目基本信息
    - 项目统计信息
    - 项目成员信息
    """
    try:
        # 检查用户权限
        if current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以执行缓存预热操作"
            )
        
        if len(project_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="一次最多只能预热100个项目的缓存"
            )
        
        results = await project_cache_service.warmup_project_cache(project_ids)
        
        return {
            "success": True,
            "data": {
                "warmup_results": results,
                "warmup_time": datetime.utcnow().isoformat()
            },
            "message": f"缓存预热完成，成功: {results['success']}, 失败: {results['failed']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预热缓存失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="预热缓存失败"
        )


# Lighthouse性能监控API

@router.post(
    "/lighthouse/audit",
    summary="运行Lighthouse性能审计",
    description="对指定URL运行Lighthouse性能审计，分析Web性能指标"
)
async def run_lighthouse_audit(
    request: LighthouseAuditRequest,
    current_user: User = Depends(get_current_user)
):
    """
    运行Lighthouse性能审计
    
    对指定的URL执行Lighthouse性能分析，包括：
    - 性能指标分析
    - 可访问性检查
    - 最佳实践评估
    - SEO优化建议
    """
    try:
        # 检查用户权限
        if current_user.role not in ["Admin", "架构师", "开发人员"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员、架构师或开发人员可以运行性能审计"
            )
        
        lighthouse_manager = await get_lighthouse_manager()
        
        # 构建配置
        config = LighthouseConfig(
            mobile=request.mobile,
            throttling=request.throttling,
            categories=request.categories or ['performance', 'accessibility', 'best-practices', 'seo']
        )
        
        # 运行审计
        result = await lighthouse_manager.run_audit(request.url, config)
        
        return {
            "success": True,
            "data": {
                "audit_id": result.audit_id,
                "url": result.url,
                "device_type": result.device_type,
                "lighthouse_version": result.lighthouse_version,
                "scores": {
                    "performance": result.scores.performance,
                    "accessibility": result.scores.accessibility,
                    "best_practices": result.scores.best_practices,
                    "seo": result.scores.seo,
                    "pwa": result.scores.pwa
                },
                "metrics": {
                    "first_contentful_paint": result.metrics.first_contentful_paint,
                    "largest_contentful_paint": result.metrics.largest_contentful_paint,
                    "cumulative_layout_shift": result.metrics.cumulative_layout_shift,
                    "first_input_delay": result.metrics.first_input_delay,
                    "speed_index": result.metrics.speed_index,
                    "total_blocking_time": result.metrics.total_blocking_time,
                    "time_to_interactive": result.metrics.time_to_interactive
                },
                "opportunities": [
                    {
                        "title": opp.title,
                        "description": opp.description,
                        "potential_savings": opp.potential_savings,
                        "audit_id": opp.audit_id
                    }
                    for opp in result.opportunities[:10]  # 只返回前10个建议
                ],
                "created_at": result.created_at.isoformat()
            },
            "message": f"性能审计完成，总体评分: {result.scores.performance}/100"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lighthouse审计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"性能审计失败: {str(e)}"
        )


@router.get(
    "/lighthouse/history/{url:path}",
    summary="获取性能历史数据",
    description="获取指定URL的Lighthouse性能历史数据"
)
async def get_lighthouse_history(
    url: str,
    days: int = Query(30, ge=1, le=365, description="历史数据天数"),
    device_type: Optional[str] = Query(None, description="设备类型过滤"),
    current_user: User = Depends(get_current_user)
):
    """
    获取性能历史数据
    
    返回指定URL的历史性能数据，包括：
    - 性能评分趋势
    - 关键指标变化
    - 设备类型对比
    """
    try:
        # 检查用户权限
        if current_user.role not in ["Admin", "架构师", "开发人员", "测试人员"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限查看性能历史数据"
            )
        
        lighthouse_manager = await get_lighthouse_manager()
        history = await lighthouse_manager.get_performance_history(url, days, device_type)
        
        if not history:
            return {
                "success": True,
                "data": {
                    "url": url,
                    "history": [],
                    "total_audits": 0,
                    "message": "没有找到历史数据"
                }
            }
        
        # 格式化历史数据
        formatted_history = []
        for h in history:
            formatted_history.append({
                "audit_id": h.audit_id,
                "device_type": h.device_type,
                "scores": {
                    "performance": h.scores.performance,
                    "accessibility": h.scores.accessibility,
                    "best_practices": h.scores.best_practices,
                    "seo": h.scores.seo
                },
                "key_metrics": {
                    "first_contentful_paint": h.metrics.first_contentful_paint,
                    "largest_contentful_paint": h.metrics.largest_contentful_paint,
                    "speed_index": h.metrics.speed_index,
                    "cumulative_layout_shift": h.metrics.cumulative_layout_shift
                },
                "created_at": h.created_at.isoformat()
            })
        
        return {
            "success": True,
            "data": {
                "url": url,
                "period_days": days,
                "device_type_filter": device_type,
                "total_audits": len(history),
                "history": formatted_history
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取性能历史数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取性能历史数据失败"
        )


@router.get(
    "/lighthouse/summary/{url:path}",
    summary="获取性能摘要",
    description="获取指定URL的性能摘要统计"
)
async def get_lighthouse_summary(
    url: str,
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    current_user: User = Depends(get_current_user)
):
    """
    获取性能摘要
    
    返回指定URL的性能摘要，包括：
    - 平均性能评分
    - 关键指标平均值
    - 性能趋势分析
    """
    try:
        # 检查用户权限
        if current_user.role not in ["Admin", "架构师", "开发人员", "测试人员"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限查看性能摘要"
            )
        
        lighthouse_manager = await get_lighthouse_manager()
        summary = await lighthouse_manager.get_performance_summary(url, days)
        
        if "error" in summary:
            return {
                "success": False,
                "error": summary["error"]
            }
        
        return {
            "success": True,
            "data": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取性能摘要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取性能摘要失败"
        )


@router.post(
    "/lighthouse/compare",
    summary="性能对比分析",
    description="对比两个时间点的性能数据"
)
async def compare_lighthouse_performance(
    request: PerformanceComparisonRequest,
    current_user: User = Depends(get_current_user)
):
    """
    性能对比分析
    
    对比指定URL在两个时间点的性能数据，包括：
    - 性能评分变化
    - 关键指标对比
    - 性能趋势分析
    """
    try:
        # 检查用户权限
        if current_user.role not in ["Admin", "架构师", "开发人员"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限进行性能对比分析"
            )
        
        lighthouse_manager = await get_lighthouse_manager()
        comparison = await lighthouse_manager.compare_performance(
            request.url,
            request.baseline_date,
            request.comparison_date
        )
        
        if "error" in comparison:
            return {
                "success": False,
                "error": comparison["error"]
            }
        
        return {
            "success": True,
            "data": comparison
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"性能对比分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="性能对比分析失败"
        )


@router.get(
    "/lighthouse/urls",
    summary="获取已测试的URL列表",
    description="获取所有已进行过Lighthouse测试的URL列表"
)
async def get_tested_urls(
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取已测试的URL列表
    
    返回所有已进行过Lighthouse测试的URL，包括：
    - URL地址
    - 最后测试时间
    - 最新性能评分
    - 测试次数
    """
    try:
        # 检查用户权限
        if current_user.role not in ["Admin", "架构师", "开发人员", "测试人员"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限查看测试URL列表"
            )
        
        from sqlalchemy import select, func, desc
        from ...models.infrastructure import LighthouseResult
        
        # 查询URL统计信息
        stmt = select(
            LighthouseResult.url,
            func.count(LighthouseResult.id).label('test_count'),
            func.max(LighthouseResult.created_at).label('last_test_time'),
            func.avg(LighthouseResult.performance_score).label('avg_performance_score')
        ).group_by(
            LighthouseResult.url
        ).order_by(
            desc('last_test_time')
        ).limit(limit)
        
        result = await db.execute(stmt)
        urls_data = result.fetchall()
        
        # 格式化结果
        urls_list = []
        for row in urls_data:
            urls_list.append({
                "url": row.url,
                "test_count": row.test_count,
                "last_test_time": row.last_test_time.isoformat() if row.last_test_time else None,
                "avg_performance_score": round(float(row.avg_performance_score), 1) if row.avg_performance_score else 0
            })
        
        return {
            "success": True,
            "data": {
                "urls": urls_list,
                "total_urls": len(urls_list)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取测试URL列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取测试URL列表失败"
        )