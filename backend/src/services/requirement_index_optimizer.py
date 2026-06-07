"""
需求管理数据库索引优化服务

提供数据库索引优化功能，包括：
- 索引创建和管理
- 索引使用情况分析
- 索引优化建议
- 索引性能监控
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, Index
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IndexInfo:
    """索引信息"""
    index_name: str
    table_name: str
    columns: List[str]
    index_type: str
    is_unique: bool
    cardinality: int
    size_mb: float
    usage_count: int
    last_used: Optional[datetime]


@dataclass
class IndexAnalysis:
    """索引分析结果"""
    index_name: str
    table_name: str
    effectiveness_score: float
    usage_frequency: int
    size_impact: float
    maintenance_cost: float
    recommendation: str  # 'keep', 'optimize', 'remove'
    reason: str


class RequirementIndexOptimizer:
    """需求管理索引优化器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # 推荐的索引配置
        self.recommended_indexes = {
            # 基础索引
            'idx_requirements_project_id': {
                'table': 'requirements',
                'columns': ['project_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirements_status': {
                'table': 'requirements',
                'columns': ['status'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirements_assignee_id': {
                'table': 'requirements',
                'columns': ['assignee_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirements_creator_id': {
                'table': 'requirements',
                'columns': ['creator_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirements_updated_at': {
                'table': 'requirements',
                'columns': ['updated_at'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirements_created_at': {
                'table': 'requirements',
                'columns': ['created_at'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            
            # 复合索引
            'idx_requirements_project_status': {
                'table': 'requirements',
                'columns': ['project_id', 'status'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirements_project_assignee': {
                'table': 'requirements',
                'columns': ['project_id', 'assignee_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirements_status_priority': {
                'table': 'requirements',
                'columns': ['status', 'priority'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirements_project_updated': {
                'table': 'requirements',
                'columns': ['project_id', 'updated_at'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            
            # 全文搜索索引
            'idx_requirements_fulltext': {
                'table': 'requirements',
                'columns': ['title', 'description', 'acceptance_criteria'],
                'type': 'fulltext',
                'unique': False,
                'priority': 'medium'
            },
            
            # 状态历史表索引
            'idx_requirement_status_history_req_id': {
                'table': 'requirement_status_history',
                'columns': ['requirement_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirement_status_history_changed_at': {
                'table': 'requirement_status_history',
                'columns': ['changed_at'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirement_status_history_changed_by': {
                'table': 'requirement_status_history',
                'columns': ['changed_by'],
                'type': 'btree',
                'unique': False,
                'priority': 'low'
            },
            
            # 依赖关系表索引
            'idx_requirement_dependencies_source': {
                'table': 'requirement_dependencies',
                'columns': ['source_requirement_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirement_dependencies_target': {
                'table': 'requirement_dependencies',
                'columns': ['target_requirement_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirement_dependencies_type': {
                'table': 'requirement_dependencies',
                'columns': ['dependency_type'],
                'type': 'btree',
                'unique': False,
                'priority': 'low'
            },
            
            # 评审表索引
            'idx_requirement_reviews_req_id': {
                'table': 'requirement_reviews',
                'columns': ['requirement_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirement_reviews_status': {
                'table': 'requirement_reviews',
                'columns': ['review_status'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirement_reviews_moderator': {
                'table': 'requirement_reviews',
                'columns': ['moderator_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirement_reviews_scheduled': {
                'table': 'requirement_reviews',
                'columns': ['scheduled_date'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            
            # 评审意见表索引
            'idx_requirement_review_comments_review': {
                'table': 'requirement_review_comments',
                'columns': ['review_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirement_review_comments_req': {
                'table': 'requirement_review_comments',
                'columns': ['requirement_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirement_review_comments_reviewer': {
                'table': 'requirement_review_comments',
                'columns': ['reviewer_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirement_review_comments_status': {
                'table': 'requirement_review_comments',
                'columns': ['status'],
                'type': 'btree',
                'unique': False,
                'priority': 'low'
            },
            
            # 变更请求表索引
            'idx_requirement_change_requests_req': {
                'table': 'requirement_change_requests',
                'columns': ['requirement_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirement_change_requests_status': {
                'table': 'requirement_change_requests',
                'columns': ['status'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirement_change_requests_requestor': {
                'table': 'requirement_change_requests',
                'columns': ['requestor_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'medium'
            },
            'idx_requirement_change_requests_requested_date': {
                'table': 'requirement_change_requests',
                'columns': ['requested_date'],
                'type': 'btree',
                'unique': False,
                'priority': 'low'
            },
            
            # 追溯链接表索引
            'idx_requirement_traceability_source': {
                'table': 'requirement_traceability_links',
                'columns': ['source_type', 'source_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirement_traceability_target': {
                'table': 'requirement_traceability_links',
                'columns': ['target_type', 'target_id'],
                'type': 'btree',
                'unique': False,
                'priority': 'high'
            },
            'idx_requirement_traceability_link_type': {
                'table': 'requirement_traceability_links',
                'columns': ['link_type'],
                'type': 'btree',
                'unique': False,
                'priority': 'low'
            }
        }
    
    async def analyze_existing_indexes(self) -> List[IndexInfo]:
        """分析现有索引"""
        try:
            # 获取需求管理相关表的索引信息
            tables = [
                'requirements', 'requirement_status_history', 'requirement_dependencies',
                'requirement_reviews', 'requirement_review_comments', 'requirement_change_requests',
                'requirement_traceability_links'
            ]
            
            all_indexes = []
            
            for table in tables:
                indexes = await self._get_table_indexes(table)
                all_indexes.extend(indexes)
            
            return all_indexes
            
        except Exception as e:
            logger.error(f"分析现有索引失败: {str(e)}")
            return []
    
    async def _get_table_indexes(self, table_name: str) -> List[IndexInfo]:
        """获取表的索引信息"""
        try:
            # 查询表的索引信息
            query = """
            SELECT 
                s.INDEX_NAME,
                s.TABLE_NAME,
                s.COLUMN_NAME,
                s.NON_UNIQUE,
                s.INDEX_TYPE,
                s.CARDINALITY,
                ROUND(
                    (SELECT SUM(data_length + index_length) / 1024 / 1024 
                     FROM information_schema.tables 
                     WHERE table_name = s.TABLE_NAME AND table_schema = DATABASE()) 
                    * s.CARDINALITY / 
                    (SELECT table_rows FROM information_schema.tables 
                     WHERE table_name = s.TABLE_NAME AND table_schema = DATABASE()), 2
                ) as SIZE_MB
            FROM information_schema.statistics s
            WHERE s.TABLE_SCHEMA = DATABASE()
            AND s.TABLE_NAME = :table_name
            ORDER BY s.INDEX_NAME, s.SEQ_IN_INDEX
            """
            
            result = await self.db.execute(text(query), {'table_name': table_name})
            rows = result.fetchall()
            
            # 按索引名分组
            indexes_dict = {}
            for row in rows:
                index_name = row.INDEX_NAME
                if index_name not in indexes_dict:
                    indexes_dict[index_name] = {
                        'index_name': index_name,
                        'table_name': row.TABLE_NAME,
                        'columns': [],
                        'index_type': row.INDEX_TYPE,
                        'is_unique': row.NON_UNIQUE == 0,
                        'cardinality': row.CARDINALITY or 0,
                        'size_mb': row.SIZE_MB or 0.0
                    }
                indexes_dict[index_name]['columns'].append(row.COLUMN_NAME)
            
            # 转换为IndexInfo对象
            indexes = []
            for index_data in indexes_dict.values():
                # 获取索引使用统计（简化实现）
                usage_stats = await self._get_index_usage_stats(index_data['index_name'], table_name)
                
                indexes.append(IndexInfo(
                    index_name=index_data['index_name'],
                    table_name=index_data['table_name'],
                    columns=index_data['columns'],
                    index_type=index_data['index_type'],
                    is_unique=index_data['is_unique'],
                    cardinality=index_data['cardinality'],
                    size_mb=index_data['size_mb'],
                    usage_count=usage_stats.get('usage_count', 0),
                    last_used=usage_stats.get('last_used')
                ))
            
            return indexes
            
        except Exception as e:
            logger.error(f"获取表 {table_name} 索引信息失败: {str(e)}")
            return []
    
    async def _get_index_usage_stats(self, index_name: str, table_name: str) -> Dict[str, Any]:
        """获取索引使用统计（简化实现）"""
        try:
            # 在实际环境中，可以查询performance_schema获取索引使用统计
            # 这里提供一个简化的实现
            query = """
            SELECT 
                COUNT_STAR as usage_count,
                LAST_UPDATE as last_used
            FROM performance_schema.table_io_waits_summary_by_index_usage
            WHERE OBJECT_SCHEMA = DATABASE()
            AND OBJECT_NAME = :table_name
            AND INDEX_NAME = :index_name
            """
            
            result = await self.db.execute(text(query), {
                'table_name': table_name,
                'index_name': index_name
            })
            row = result.fetchone()
            
            if row:
                return {
                    'usage_count': row.usage_count or 0,
                    'last_used': row.last_used
                }
            else:
                return {'usage_count': 0, 'last_used': None}
                
        except Exception as e:
            # 如果performance_schema不可用，返回默认值
            logger.debug(f"无法获取索引使用统计: {str(e)}")
            return {'usage_count': 0, 'last_used': None}
    
    async def analyze_index_effectiveness(self) -> List[IndexAnalysis]:
        """分析索引有效性"""
        existing_indexes = await self.analyze_existing_indexes()
        analyses = []
        
        for index in existing_indexes:
            # 跳过主键和唯一约束索引
            if index.index_name == 'PRIMARY' or 'unique' in index.index_name.lower():
                continue
            
            analysis = await self._analyze_single_index(index)
            analyses.append(analysis)
        
        return analyses
    
    async def _analyze_single_index(self, index: IndexInfo) -> IndexAnalysis:
        """分析单个索引"""
        # 计算有效性评分
        effectiveness_score = self._calculate_effectiveness_score(index)
        
        # 计算维护成本
        maintenance_cost = self._calculate_maintenance_cost(index)
        
        # 生成建议
        recommendation, reason = self._generate_index_recommendation(
            index, effectiveness_score, maintenance_cost
        )
        
        return IndexAnalysis(
            index_name=index.index_name,
            table_name=index.table_name,
            effectiveness_score=effectiveness_score,
            usage_frequency=index.usage_count,
            size_impact=index.size_mb,
            maintenance_cost=maintenance_cost,
            recommendation=recommendation,
            reason=reason
        )
    
    def _calculate_effectiveness_score(self, index: IndexInfo) -> float:
        """计算索引有效性评分"""
        score = 0.0
        
        # 基于使用频率
        if index.usage_count > 1000:
            score += 0.4
        elif index.usage_count > 100:
            score += 0.3
        elif index.usage_count > 10:
            score += 0.2
        elif index.usage_count > 0:
            score += 0.1
        
        # 基于基数
        if index.cardinality > 10000:
            score += 0.3
        elif index.cardinality > 1000:
            score += 0.2
        elif index.cardinality > 100:
            score += 0.1
        
        # 基于列数（复合索引）
        if len(index.columns) == 1:
            score += 0.1
        elif len(index.columns) == 2:
            score += 0.2
        elif len(index.columns) >= 3:
            score += 0.1  # 过多列可能降低效率
        
        # 基于索引类型
        if index.index_type == 'BTREE':
            score += 0.2
        elif index.index_type == 'FULLTEXT':
            score += 0.1
        
        return min(1.0, score)
    
    def _calculate_maintenance_cost(self, index: IndexInfo) -> float:
        """计算索引维护成本"""
        cost = 0.0
        
        # 基于大小
        if index.size_mb > 100:
            cost += 0.4
        elif index.size_mb > 50:
            cost += 0.3
        elif index.size_mb > 10:
            cost += 0.2
        else:
            cost += 0.1
        
        # 基于列数
        cost += len(index.columns) * 0.1
        
        # 基于表的写入频率（简化评估）
        if index.table_name == 'requirements':
            cost += 0.2  # 主表写入较频繁
        elif 'history' in index.table_name:
            cost += 0.3  # 历史表写入很频繁
        else:
            cost += 0.1
        
        return min(1.0, cost)
    
    def _generate_index_recommendation(self, index: IndexInfo, 
                                     effectiveness_score: float, 
                                     maintenance_cost: float) -> tuple[str, str]:
        """生成索引建议"""
        # 计算收益成本比
        benefit_cost_ratio = effectiveness_score / max(maintenance_cost, 0.1)
        
        if effectiveness_score < 0.2 and index.usage_count == 0:
            return 'remove', f'索引未被使用且有效性低 (评分: {effectiveness_score:.2f})'
        elif benefit_cost_ratio < 0.5:
            return 'optimize', f'索引收益成本比较低 (比率: {benefit_cost_ratio:.2f})'
        elif effectiveness_score > 0.7:
            return 'keep', f'索引效果良好 (评分: {effectiveness_score:.2f})'
        else:
            return 'keep', f'索引表现一般但可保留 (评分: {effectiveness_score:.2f})'
    
    async def create_recommended_indexes(self, priority_filter: str = 'high') -> Dict[str, Any]:
        """创建推荐的索引"""
        results = {
            'created': [],
            'skipped': [],
            'errors': []
        }
        
        # 获取现有索引
        existing_indexes = await self.analyze_existing_indexes()
        existing_index_names = {idx.index_name for idx in existing_indexes}
        
        for index_name, config in self.recommended_indexes.items():
            # 根据优先级过滤
            if priority_filter != 'all' and config['priority'] != priority_filter:
                continue
            
            # 检查索引是否已存在
            if index_name in existing_index_names:
                results['skipped'].append({
                    'index_name': index_name,
                    'reason': '索引已存在'
                })
                continue
            
            try:
                await self._create_index(index_name, config)
                results['created'].append({
                    'index_name': index_name,
                    'table': config['table'],
                    'columns': config['columns']
                })
                logger.info(f"成功创建索引: {index_name}")
                
            except Exception as e:
                error_msg = f"创建索引 {index_name} 失败: {str(e)}"
                results['errors'].append({
                    'index_name': index_name,
                    'error': error_msg
                })
                logger.error(error_msg)
        
        return results
    
    async def _create_index(self, index_name: str, config: Dict[str, Any]):
        """创建单个索引"""
        table = config['table']
        columns = config['columns']
        index_type = config['type']
        is_unique = config.get('unique', False)
        
        # 构建创建索引的SQL
        if index_type == 'fulltext':
            sql = f"CREATE FULLTEXT INDEX {index_name} ON {table} ({', '.join(columns)})"
        else:
            unique_keyword = 'UNIQUE ' if is_unique else ''
            sql = f"CREATE {unique_keyword}INDEX {index_name} ON {table} ({', '.join(columns)})"
        
        await self.db.execute(text(sql))
        await self.db.commit()
    
    async def drop_unused_indexes(self, min_usage_threshold: int = 0) -> Dict[str, Any]:
        """删除未使用的索引"""
        results = {
            'dropped': [],
            'skipped': [],
            'errors': []
        }
        
        analyses = await self.analyze_index_effectiveness()
        
        for analysis in analyses:
            # 跳过主键和系统索引
            if (analysis.index_name == 'PRIMARY' or 
                analysis.index_name.startswith('fk_') or
                'unique' in analysis.index_name.lower()):
                continue
            
            # 检查是否应该删除
            if (analysis.usage_frequency <= min_usage_threshold and 
                analysis.effectiveness_score < 0.2):
                
                try:
                    await self._drop_index(analysis.index_name, analysis.table_name)
                    results['dropped'].append({
                        'index_name': analysis.index_name,
                        'table_name': analysis.table_name,
                        'reason': f'使用频率: {analysis.usage_frequency}, 有效性: {analysis.effectiveness_score:.2f}'
                    })
                    logger.info(f"成功删除索引: {analysis.index_name}")
                    
                except Exception as e:
                    error_msg = f"删除索引 {analysis.index_name} 失败: {str(e)}"
                    results['errors'].append({
                        'index_name': analysis.index_name,
                        'error': error_msg
                    })
                    logger.error(error_msg)
            else:
                results['skipped'].append({
                    'index_name': analysis.index_name,
                    'reason': f'索引仍有价值 (使用: {analysis.usage_frequency}, 有效性: {analysis.effectiveness_score:.2f})'
                })
        
        return results
    
    async def _drop_index(self, index_name: str, table_name: str):
        """删除单个索引"""
        sql = f"DROP INDEX {index_name} ON {table_name}"
        await self.db.execute(text(sql))
        await self.db.commit()
    
    async def optimize_table_indexes(self, table_name: str) -> Dict[str, Any]:
        """优化表的索引"""
        try:
            # 分析表
            sql = f"ANALYZE TABLE {table_name}"
            await self.db.execute(text(sql))
            
            # 优化表
            sql = f"OPTIMIZE TABLE {table_name}"
            result = await self.db.execute(text(sql))
            
            await self.db.commit()
            
            return {
                'table_name': table_name,
                'status': 'success',
                'message': '表索引优化完成'
            }
            
        except Exception as e:
            logger.error(f"优化表 {table_name} 索引失败: {str(e)}")
            return {
                'table_name': table_name,
                'status': 'error',
                'message': str(e)
            }
    
    async def get_index_optimization_report(self) -> Dict[str, Any]:
        """获取索引优化报告"""
        try:
            existing_indexes = await self.analyze_existing_indexes()
            analyses = await self.analyze_index_effectiveness()
            
            # 统计信息
            total_indexes = len(existing_indexes)
            total_size_mb = sum(idx.size_mb for idx in existing_indexes)
            unused_indexes = [a for a in analyses if a.usage_frequency == 0]
            ineffective_indexes = [a for a in analyses if a.effectiveness_score < 0.3]
            
            # 推荐操作
            recommendations = {
                'create': [],
                'optimize': [],
                'remove': []
            }
            
            for analysis in analyses:
                if analysis.recommendation == 'remove':
                    recommendations['remove'].append({
                        'index_name': analysis.index_name,
                        'table_name': analysis.table_name,
                        'reason': analysis.reason,
                        'size_mb': analysis.size_impact
                    })
                elif analysis.recommendation == 'optimize':
                    recommendations['optimize'].append({
                        'index_name': analysis.index_name,
                        'table_name': analysis.table_name,
                        'reason': analysis.reason,
                        'effectiveness_score': analysis.effectiveness_score
                    })
            
            # 检查缺失的推荐索引
            existing_index_names = {idx.index_name for idx in existing_indexes}
            for index_name, config in self.recommended_indexes.items():
                if index_name not in existing_index_names and config['priority'] == 'high':
                    recommendations['create'].append({
                        'index_name': index_name,
                        'table_name': config['table'],
                        'columns': config['columns'],
                        'priority': config['priority']
                    })
            
            return {
                'summary': {
                    'total_indexes': total_indexes,
                    'total_size_mb': round(total_size_mb, 2),
                    'unused_indexes_count': len(unused_indexes),
                    'ineffective_indexes_count': len(ineffective_indexes),
                    'potential_savings_mb': round(sum(a.size_impact for a in analyses if a.recommendation == 'remove'), 2)
                },
                'recommendations': recommendations,
                'index_analyses': [
                    {
                        'index_name': a.index_name,
                        'table_name': a.table_name,
                        'effectiveness_score': round(a.effectiveness_score, 2),
                        'usage_frequency': a.usage_frequency,
                        'size_mb': round(a.size_impact, 2),
                        'maintenance_cost': round(a.maintenance_cost, 2),
                        'recommendation': a.recommendation,
                        'reason': a.reason
                    }
                    for a in analyses
                ]
            }
            
        except Exception as e:
            logger.error(f"生成索引优化报告失败: {str(e)}")
            return {
                'error': str(e),
                'summary': {},
                'recommendations': {'create': [], 'optimize': [], 'remove': []},
                'index_analyses': []
            }
    
    async def create_missing_indexes(self) -> Dict[str, Any]:
        """创建缺失的重要索引"""
        return await self.create_recommended_indexes(priority_filter='high')
    
    async def get_slow_query_index_suggestions(self, slow_queries: List[str]) -> List[Dict[str, Any]]:
        """基于慢查询分析索引建议"""
        suggestions = []
        
        for query in slow_queries:
            # 简化的查询分析 - 在实际环境中可以使用更复杂的SQL解析
            query_lower = query.lower()
            
            if 'where project_id' in query_lower and 'status' in query_lower:
                suggestions.append({
                    'suggested_index': 'idx_requirements_project_status',
                    'table': 'requirements',
                    'columns': ['project_id', 'status'],
                    'reason': '查询频繁使用项目ID和状态条件',
                    'query_pattern': 'WHERE project_id = ? AND status = ?'
                })
            
            if 'where assignee_id' in query_lower:
                suggestions.append({
                    'suggested_index': 'idx_requirements_assignee_id',
                    'table': 'requirements',
                    'columns': ['assignee_id'],
                    'reason': '查询频繁使用负责人ID条件',
                    'query_pattern': 'WHERE assignee_id = ?'
                })
            
            if 'order by updated_at' in query_lower:
                suggestions.append({
                    'suggested_index': 'idx_requirements_updated_at',
                    'table': 'requirements',
                    'columns': ['updated_at'],
                    'reason': '查询频繁按更新时间排序',
                    'query_pattern': 'ORDER BY updated_at'
                })
        
        # 去重
        unique_suggestions = []
        seen_indexes = set()
        for suggestion in suggestions:
            if suggestion['suggested_index'] not in seen_indexes:
                unique_suggestions.append(suggestion)
                seen_indexes.add(suggestion['suggested_index'])
        
        return unique_suggestions