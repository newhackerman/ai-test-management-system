"""
智能缺陷分析服务

本模块实现了缺陷的智能分析功能，包括：
- AI辅助缺陷分类和严重程度评估
- 基于历史数据的智能分配建议
- 缺陷相似性检测和重复识别
- 缺陷根因分析和分类统计
"""
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
# 可选的机器学习依赖
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # 提供简单的替代实现
    TfidfVectorizer = None
    cosine_similarity = None
    np = None

from ..models.test_case import Defect, DefectStatus, DefectSeverity, DefectType, TestCasePriority
from ..models.user import User
from ..schemas.defect import (
    DefectAnalysisResult, DefectAssignmentSuggestion, DefectSimilarityResult,
    CreateDefectRequest
)
from ..core.exceptions import ValidationError
from ..utils.redis_client import RedisClient
from .ai_assistant_service import AIAssistantService

logger = logging.getLogger(__name__)

class DefectAnalysisService:
    """智能缺陷分析服务"""
    
    def __init__(self, db: Session, redis_client: RedisClient, ai_service: AIAssistantService):
        self.db = db
        self.redis = redis_client
        self.ai_service = ai_service
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        else:
            self.vectorizer = None
    
    async def analyze_defect_with_ai(self, defect_data: CreateDefectRequest) -> DefectAnalysisResult:
        """使用AI分析缺陷"""
        try:
            # 1. 构建分析提示词
            analysis_prompt = self._build_analysis_prompt(defect_data)
            
            # 2. 调用AI服务进行分析
            ai_response = await self.ai_service.analyze_text(analysis_prompt)
            
            # 3. 解析AI响应
            analysis_result = self._parse_ai_analysis_response(ai_response)
            
            # 4. 检测相似缺陷
            similar_defects = await self._find_similar_defects(defect_data)
            analysis_result.similar_defects = similar_defects
            
            # 5. 缓存分析结果
            await self._cache_analysis_result(defect_data, analysis_result)
            
            logger.info(f"AI缺陷分析完成，置信度: {analysis_result.confidence}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"AI缺陷分析失败: {str(e)}")
            # 返回基础分析结果
            return await self._fallback_analysis(defect_data)
    
    async def suggest_defect_assignment(self, defect_data: CreateDefectRequest, 
                                       ai_analysis: DefectAnalysisResult) -> DefectAssignmentSuggestion:
        """智能缺陷分配建议"""
        try:
            # 1. 如果已指定分配人，验证并返回
            if defect_data.assignee_id:
                return await self._validate_manual_assignment(defect_data.assignee_id)
            
            # 2. 获取候选分配人列表
            candidates = await self._get_assignment_candidates(defect_data, ai_analysis)
            
            # 3. 计算每个候选人的分配分数
            scored_candidates = []
            for candidate in candidates:
                score = await self._calculate_assignment_score(candidate, defect_data, ai_analysis)
                scored_candidates.append((candidate, score))
            
            # 4. 选择最佳分配人
            if scored_candidates:
                best_candidate, best_score = max(scored_candidates, key=lambda x: x[1]['total_score'])
                
                return DefectAssignmentSuggestion(
                    assignee_id=best_candidate.id,
                    assignee_name=best_candidate.username,
                    confidence=best_score['confidence'],
                    reason=best_score['reason'],
                    workload=best_score['workload'],
                    expertise_match=best_score['expertise_match']
                )
            
            # 5. 如果没有合适的候选人，返回默认分配
            return await self._get_default_assignment()
            
        except Exception as e:
            logger.error(f"智能分配建议失败: {str(e)}")
            return await self._get_default_assignment()
    
    async def find_similar_defects(self, defect_data: CreateDefectRequest, 
                                  threshold: float = 0.7) -> List[DefectSimilarityResult]:
        """查找相似缺陷"""
        try:
            # 1. 获取历史缺陷数据
            historical_defects = await self._get_historical_defects_for_similarity()
            
            if not historical_defects:
                return []
            
            if SKLEARN_AVAILABLE and self.vectorizer:
                # 使用机器学习方法计算相似度
                # 2. 构建文本特征
                current_text = self._build_defect_text(defect_data)
                historical_texts = [self._build_defect_text_from_model(d) for d in historical_defects]
                
                # 3. 计算文本相似度
                all_texts = [current_text] + historical_texts
                tfidf_matrix = self.vectorizer.fit_transform(all_texts)
                
                # 4. 计算余弦相似度
                similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            else:
                # 使用简单的文本匹配方法
                current_text = self._build_defect_text(defect_data)
                similarities = []
                for defect in historical_defects:
                    historical_text = self._build_defect_text_from_model(defect)
                    similarity = self._simple_text_similarity(current_text, historical_text)
                    similarities.append(similarity)
            
            # 5. 筛选相似度高的缺陷
            similar_defects = []
            for i, similarity in enumerate(similarities):
                if similarity >= threshold:
                    defect = historical_defects[i]
                    similar_defects.append(DefectSimilarityResult(
                        similar_defect_id=defect.id,
                        similar_defect_code=defect.defect_code,
                        similar_defect_title=defect.title,
                        similarity_score=float(similarity),
                        similarity_reasons=self._analyze_similarity_reasons(defect_data, defect, similarity)
                    ))
            
            # 6. 按相似度排序
            similar_defects.sort(key=lambda x: x.similarity_score, reverse=True)
            
            logger.info(f"找到 {len(similar_defects)} 个相似缺陷")
            return similar_defects[:5]  # 返回前5个最相似的
            
        except Exception as e:
            logger.error(f"查找相似缺陷失败: {str(e)}")
            return []
    
    async def analyze_defect_root_cause(self, defect_id: int) -> Dict[str, Any]:
        """分析缺陷根因"""
        try:
            # 1. 获取缺陷信息
            defect = self.db.query(Defect).filter(Defect.id == defect_id).first()
            if not defect:
                raise ValidationError("缺陷不存在")
            
            # 2. 构建根因分析提示词
            root_cause_prompt = self._build_root_cause_prompt(defect)
            
            # 3. 调用AI进行根因分析
            ai_response = await self.ai_service.analyze_text(root_cause_prompt)
            
            # 4. 解析根因分析结果
            root_cause_analysis = self._parse_root_cause_response(ai_response)
            
            # 5. 获取相关统计数据
            related_stats = await self._get_related_defect_stats(defect)
            
            # 6. 合并分析结果
            analysis_result = {
                'defect_id': defect_id,
                'root_cause': root_cause_analysis.get('root_cause'),
                'contributing_factors': root_cause_analysis.get('contributing_factors', []),
                'prevention_suggestions': root_cause_analysis.get('prevention_suggestions', []),
                'related_statistics': related_stats,
                'confidence': root_cause_analysis.get('confidence', 0.5),
                'analyzed_at': datetime.utcnow()
            }
            
            # 7. 缓存分析结果
            await self._cache_root_cause_analysis(defect_id, analysis_result)
            
            logger.info(f"缺陷根因分析完成: {defect.defect_code}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"缺陷根因分析失败: {str(e)}")
            raise ValidationError(f"缺陷根因分析失败: {str(e)}")
    
    async def classify_defects_by_pattern(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """按模式分类缺陷"""
        try:
            # 1. 获取缺陷数据
            query = self.db.query(Defect)
            if project_id:
                # 通过关联获取项目缺陷
                query = query.join(Defect.test_case).filter(TestCase.project_id == project_id)
            
            defects = query.filter(
                Defect.created_at >= datetime.utcnow() - timedelta(days=90)  # 最近90天
            ).all()
            
            # 2. 按不同维度分类
            classification_result = {
                'by_type': self._classify_by_type(defects),
                'by_severity': self._classify_by_severity(defects),
                'by_module': self._classify_by_module(defects),
                'by_root_cause': await self._classify_by_root_cause(defects),
                'by_time_pattern': self._classify_by_time_pattern(defects),
                'by_reporter': self._classify_by_reporter(defects),
                'by_resolution_time': self._classify_by_resolution_time(defects)
            }
            
            # 3. 生成分类洞察
            insights = await self._generate_classification_insights(classification_result)
            classification_result['insights'] = insights
            
            # 4. 缓存分类结果
            await self._cache_classification_result(project_id, classification_result)
            
            logger.info(f"缺陷模式分类完成，共分析 {len(defects)} 个缺陷")
            return classification_result
            
        except Exception as e:
            logger.error(f"缺陷模式分类失败: {str(e)}")
            raise ValidationError(f"缺陷模式分类失败: {str(e)}")
    
    # 私有方法实现
    def _build_analysis_prompt(self, defect_data: CreateDefectRequest) -> str:
        """构建AI分析提示词"""
        prompt = f"""
        请分析以下缺陷信息，并提供详细的分类和评估建议：

        缺陷标题: {defect_data.title}
        缺陷描述: {defect_data.description}
        重现步骤: {defect_data.steps_to_reproduce or '无'}
        测试环境: {defect_data.test_environment or '无'}
        当前分类: {defect_data.defect_type.value}
        当前严重程度: {defect_data.severity.value}
        当前优先级: {defect_data.priority.value}

        请提供以下分析：
        1. 建议的缺陷类型（FUNCTIONAL/PERFORMANCE/SECURITY/USABILITY/COMPATIBILITY/DATA/INTERFACE）
        2. 建议的严重程度（CRITICAL/HIGH/MEDIUM/LOW）
        3. 建议的优先级（CRITICAL/HIGH/MEDIUM/LOW）
        4. 根因分析（可能的原因）
        5. 修复建议（具体的修复步骤）
        6. 预防措施（如何避免类似问题）
        7. 分析置信度（0-1之间的数值）

        请以JSON格式返回结果。
        """
        return prompt
    
    def _parse_ai_analysis_response(self, ai_response: str) -> DefectAnalysisResult:
        """解析AI分析响应"""
        try:
            # 尝试解析JSON响应
            import json
            if ai_response.strip().startswith('{'):
                response_data = json.loads(ai_response)
                return DefectAnalysisResult(
                    suggested_type=self._parse_defect_type(response_data.get('defect_type')),
                    suggested_severity=self._parse_severity(response_data.get('severity')),
                    suggested_priority=self._parse_priority(response_data.get('priority')),
                    root_cause_analysis=response_data.get('root_cause'),
                    fix_suggestions=response_data.get('fix_suggestions', []),
                    confidence=float(response_data.get('confidence', 0.5))
                )
        except:
            pass
        
        # 如果JSON解析失败，使用文本解析
        return DefectAnalysisResult(
            suggested_type=self._extract_defect_type_from_text(ai_response),
            suggested_severity=self._extract_severity_from_text(ai_response),
            suggested_priority=self._extract_priority_from_text(ai_response),
            root_cause_analysis=self._extract_root_cause_from_text(ai_response),
            fix_suggestions=self._extract_fix_suggestions_from_text(ai_response),
            confidence=0.6  # 默认置信度
        )
    
    async def _fallback_analysis(self, defect_data: CreateDefectRequest) -> DefectAnalysisResult:
        """备用分析方法"""
        # 基于关键词的简单分析
        title_desc = f"{defect_data.title} {defect_data.description}".lower()
        
        # 分析缺陷类型
        suggested_type = None
        if any(word in title_desc for word in ['crash', 'error', 'exception', 'fail']):
            suggested_type = DefectType.FUNCTIONAL
        elif any(word in title_desc for word in ['slow', 'performance', 'timeout']):
            suggested_type = DefectType.PERFORMANCE
        elif any(word in title_desc for word in ['security', 'vulnerability', 'auth']):
            suggested_type = DefectType.SECURITY
        
        # 分析严重程度
        suggested_severity = None
        if any(word in title_desc for word in ['critical', 'severe', 'crash', 'data loss']):
            suggested_severity = DefectSeverity.CRITICAL
        elif any(word in title_desc for word in ['major', 'important', 'block']):
            suggested_severity = DefectSeverity.HIGH
        
        return DefectAnalysisResult(
            suggested_type=suggested_type,
            suggested_severity=suggested_severity,
            suggested_priority=None,
            root_cause_analysis="基于关键词的简单分析",
            fix_suggestions=["请详细检查相关代码", "添加必要的错误处理"],
            confidence=0.3
        )
    
    async def _validate_manual_assignment(self, assignee_id: int) -> DefectAssignmentSuggestion:
        """验证手动分配"""
        assignee = self.db.query(User).filter(User.id == assignee_id).first()
        if not assignee:
            raise ValidationError("指定的分配人不存在")
        
        # 获取当前工作负载
        workload = self.db.query(Defect).filter(
            Defect.assignee_id == assignee_id,
            Defect.status.in_([DefectStatus.ASSIGNED, DefectStatus.IN_PROGRESS])
        ).count()
        
        return DefectAssignmentSuggestion(
            assignee_id=assignee_id,
            assignee_name=assignee.username,
            confidence=1.0,
            reason="手动指定",
            workload=workload,
            expertise_match=1.0
        )
    
    async def _get_assignment_candidates(self, defect_data: CreateDefectRequest, 
                                       ai_analysis: DefectAnalysisResult) -> List[User]:
        """获取分配候选人"""
        # 获取活跃的开发人员
        candidates = self.db.query(User).filter(
            User.is_active == True,
            User.id != 1  # 排除系统管理员
        ).all()
        
        # 根据缺陷类型筛选专业匹配的候选人
        if ai_analysis.suggested_type:
            # 这里可以根据用户的专业技能进行筛选
            # 简化实现，返回所有候选人
            pass
        
        return candidates
    
    async def _calculate_assignment_score(self, candidate: User, defect_data: CreateDefectRequest,
                                        ai_analysis: DefectAnalysisResult) -> Dict[str, Any]:
        """计算分配分数"""
        # 1. 计算工作负载分数
        current_workload = self.db.query(Defect).filter(
            Defect.assignee_id == candidate.id,
            Defect.status.in_([DefectStatus.ASSIGNED, DefectStatus.IN_PROGRESS])
        ).count()
        
        workload_score = max(0, 1 - (current_workload / 10))  # 假设10个是满负载
        
        # 2. 计算专业匹配分数
        expertise_score = await self._calculate_expertise_match(candidate, defect_data, ai_analysis)
        
        # 3. 计算历史表现分数
        performance_score = await self._calculate_historical_performance(candidate)
        
        # 4. 计算综合分数
        total_score = (workload_score * 0.4 + expertise_score * 0.4 + performance_score * 0.2)
        
        # 5. 生成推荐理由
        reason_parts = []
        if workload_score > 0.7:
            reason_parts.append("工作负载适中")
        if expertise_score > 0.7:
            reason_parts.append("专业技能匹配")
        if performance_score > 0.7:
            reason_parts.append("历史表现良好")
        
        reason = "、".join(reason_parts) if reason_parts else "综合评估推荐"
        
        return {
            'total_score': total_score,
            'workload': current_workload,
            'expertise_match': expertise_score,
            'confidence': min(0.9, total_score + 0.1),
            'reason': reason
        }
    
    async def _calculate_expertise_match(self, candidate: User, defect_data: CreateDefectRequest,
                                       ai_analysis: DefectAnalysisResult) -> float:
        """计算专业匹配度"""
        # 简化实现：基于用户名和历史处理的缺陷类型
        match_score = 0.5  # 基础分数
        
        # 根据缺陷类型调整分数
        if ai_analysis.suggested_type:
            # 统计该用户处理过的相同类型缺陷数量
            same_type_count = self.db.query(Defect).filter(
                Defect.assignee_id == candidate.id,
                Defect.defect_type == ai_analysis.suggested_type,
                Defect.status == DefectStatus.CLOSED
            ).count()
            
            if same_type_count > 0:
                match_score += min(0.4, same_type_count * 0.1)
        
        # 根据用户名进行简单匹配（实际应用中应该基于用户技能标签）
        username_lower = candidate.username.lower()
        if 'frontend' in username_lower and ai_analysis.suggested_type == DefectType.USABILITY:
            match_score += 0.2
        elif 'backend' in username_lower and ai_analysis.suggested_type == DefectType.PERFORMANCE:
            match_score += 0.2
        elif 'security' in username_lower and ai_analysis.suggested_type == DefectType.SECURITY:
            match_score += 0.3
        
        return min(1.0, match_score)
    
    async def _calculate_historical_performance(self, candidate: User) -> float:
        """计算历史表现分数"""
        # 获取最近30天的缺陷处理情况
        recent_defects = self.db.query(Defect).filter(
            Defect.assignee_id == candidate.id,
            Defect.resolved_at >= datetime.utcnow() - timedelta(days=30)
        ).all()
        
        if not recent_defects:
            return 0.5  # 没有历史数据，给中等分数
        
        # 计算平均解决时间
        resolution_times = []
        for defect in recent_defects:
            if defect.resolved_at and defect.assigned_at:
                resolution_time = (defect.resolved_at - defect.assigned_at).total_seconds() / 3600
                resolution_times.append(resolution_time)
        
        if resolution_times:
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
            # 假设24小时内解决是优秀的
            time_score = max(0, 1 - (avg_resolution_time / 24))
        else:
            time_score = 0.5
        
        # 计算重开率
        reopened_count = len([d for d in recent_defects if d.status == DefectStatus.REOPENED])
        reopen_rate = reopened_count / len(recent_defects)
        reopen_score = max(0, 1 - reopen_rate * 2)
        
        return (time_score + reopen_score) / 2
    
    async def _get_default_assignment(self) -> DefectAssignmentSuggestion:
        """获取默认分配"""
        # 返回系统管理员作为默认分配
        admin = self.db.query(User).filter(User.is_superuser == True).first()
        if admin:
            return DefectAssignmentSuggestion(
                assignee_id=admin.id,
                assignee_name=admin.username,
                confidence=0.1,
                reason="无合适候选人，分配给管理员",
                workload=0,
                expertise_match=0.1
            )
        
        # 如果没有管理员，返回ID为1的用户
        return DefectAssignmentSuggestion(
            assignee_id=1,
            assignee_name="系统管理员",
            confidence=0.1,
            reason="系统默认分配",
            workload=0,
            expertise_match=0.1
        )
    
    async def _get_historical_defects_for_similarity(self) -> List[Defect]:
        """获取用于相似性比较的历史缺陷"""
        # 获取最近6个月的缺陷，排除当前正在创建的
        return self.db.query(Defect).filter(
            Defect.created_at >= datetime.utcnow() - timedelta(days=180)
        ).order_by(desc(Defect.created_at)).limit(1000).all()
    
    def _build_defect_text(self, defect_data: CreateDefectRequest) -> str:
        """构建缺陷文本用于相似性比较"""
        text_parts = [defect_data.title, defect_data.description]
        if defect_data.steps_to_reproduce:
            text_parts.append(defect_data.steps_to_reproduce)
        return " ".join(text_parts)
    
    def _build_defect_text_from_model(self, defect: Defect) -> str:
        """从缺陷模型构建文本"""
        text_parts = [defect.title, defect.description]
        if defect.steps_to_reproduce:
            text_parts.append(defect.steps_to_reproduce)
        return " ".join(text_parts)
    
    def _analyze_similarity_reasons(self, current_defect: CreateDefectRequest, 
                                   similar_defect: Defect, similarity_score: float) -> List[str]:
        """分析相似性原因"""
        reasons = []
        
        # 检查标题相似性
        if self._calculate_text_similarity(current_defect.title, similar_defect.title) > 0.5:
            reasons.append("标题相似")
        
        # 检查类型相同
        if current_defect.defect_type == similar_defect.defect_type:
            reasons.append("缺陷类型相同")
        
        # 检查严重程度相同
        if current_defect.severity == similar_defect.severity:
            reasons.append("严重程度相同")
        
        # 检查关键词重叠
        current_keywords = set(re.findall(r'\w+', current_defect.description.lower()))
        similar_keywords = set(re.findall(r'\w+', similar_defect.description.lower()))
        common_keywords = current_keywords.intersection(similar_keywords)
        if len(common_keywords) > 3:
            reasons.append(f"关键词重叠: {', '.join(list(common_keywords)[:3])}")
        
        if not reasons:
            reasons.append("文本内容相似")
        
        return reasons
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        if SKLEARN_AVAILABLE:
            try:
                vectorizer = TfidfVectorizer()
                tfidf_matrix = vectorizer.fit_transform([text1, text2])
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                return float(similarity)
            except:
                return 0.0
        else:
            # 使用简单的文本相似度计算
            return self._simple_text_similarity(text1, text2)
    
    def _simple_text_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度计算（不依赖sklearn）"""
        if not text1 or not text2:
            return 0.0
        
        # 转换为小写并分词
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        # 计算Jaccard相似度
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    # 文本解析辅助方法
    def _parse_defect_type(self, type_str: str) -> Optional[DefectType]:
        """解析缺陷类型"""
        if not type_str:
            return None
        type_str = type_str.upper()
        for defect_type in DefectType:
            if defect_type.value in type_str:
                return defect_type
        return None
    
    def _parse_severity(self, severity_str: str) -> Optional[DefectSeverity]:
        """解析严重程度"""
        if not severity_str:
            return None
        severity_str = severity_str.upper()
        for severity in DefectSeverity:
            if severity.value in severity_str:
                return severity
        return None
    
    def _parse_priority(self, priority_str: str) -> Optional[TestCasePriority]:
        """解析优先级"""
        if not priority_str:
            return None
        priority_str = priority_str.upper()
        for priority in TestCasePriority:
            if priority.value in priority_str:
                return priority
        return None
    
    def _extract_defect_type_from_text(self, text: str) -> Optional[DefectType]:
        """从文本中提取缺陷类型"""
        text_upper = text.upper()
        for defect_type in DefectType:
            if defect_type.value in text_upper:
                return defect_type
        return None
    
    def _extract_severity_from_text(self, text: str) -> Optional[DefectSeverity]:
        """从文本中提取严重程度"""
        text_upper = text.upper()
        for severity in DefectSeverity:
            if severity.value in text_upper:
                return severity
        return None
    
    def _extract_priority_from_text(self, text: str) -> Optional[TestCasePriority]:
        """从文本中提取优先级"""
        text_upper = text.upper()
        for priority in TestCasePriority:
            if priority.value in text_upper:
                return priority
        return None
    
    def _extract_root_cause_from_text(self, text: str) -> Optional[str]:
        """从文本中提取根因分析"""
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['根因', 'root cause', '原因']):
                return line.strip()
        return None
    
    def _extract_fix_suggestions_from_text(self, text: str) -> Optional[List[str]]:
        """从文本中提取修复建议"""
        suggestions = []
        lines = text.split('\n')
        in_suggestions = False
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['修复建议', 'fix suggestion', '解决方案']):
                in_suggestions = True
                continue
            
            if in_suggestions and line.strip():
                if line.strip().startswith(('-', '•', '1.', '2.', '3.')):
                    suggestions.append(line.strip())
                elif not any(keyword in line.lower() for keyword in ['分析', 'analysis', '总结']):
                    suggestions.append(line.strip())
        
        return suggestions if suggestions else None
    
    # 缓存相关方法
    async def _cache_analysis_result(self, defect_data: CreateDefectRequest, result: DefectAnalysisResult):
        """缓存分析结果"""
        try:
            cache_key = f"defect_analysis:{hash(defect_data.title + defect_data.description)}"
            await self.redis.setex(cache_key, 3600, result.json())
        except Exception as e:
            logger.warning(f"缓存分析结果失败: {str(e)}")
    
    async def _cache_root_cause_analysis(self, defect_id: int, analysis: Dict[str, Any]):
        """缓存根因分析结果"""
        try:
            cache_key = f"defect_root_cause:{defect_id}"
            import json
            await self.redis.setex(cache_key, 7200, json.dumps(analysis, default=str))
        except Exception as e:
            logger.warning(f"缓存根因分析失败: {str(e)}")
    
    async def _cache_classification_result(self, project_id: Optional[int], result: Dict[str, Any]):
        """缓存分类结果"""
        try:
            cache_key = f"defect_classification:{project_id or 'all'}"
            import json
            await self.redis.setex(cache_key, 3600, json.dumps(result, default=str))
        except Exception as e:
            logger.warning(f"缓存分类结果失败: {str(e)}")
    
    # 其他分析方法的占位符实现
    def _build_root_cause_prompt(self, defect: Defect) -> str:
        """构建根因分析提示词"""
        return f"请分析缺陷 '{defect.title}' 的根本原因..."
    
    def _parse_root_cause_response(self, response: str) -> Dict[str, Any]:
        """解析根因分析响应"""
        return {'root_cause': '待实现', 'confidence': 0.5}
    
    async def _get_related_defect_stats(self, defect: Defect) -> Dict[str, Any]:
        """获取相关缺陷统计"""
        return {'related_count': 0}
    
    def _classify_by_type(self, defects: List[Defect]) -> Dict[str, int]:
        """按类型分类"""
        classification = {}
        for defect in defects:
            type_name = defect.defect_type.value
            classification[type_name] = classification.get(type_name, 0) + 1
        return classification
    
    def _classify_by_severity(self, defects: List[Defect]) -> Dict[str, int]:
        """按严重程度分类"""
        classification = {}
        for defect in defects:
            severity_name = defect.severity.value
            classification[severity_name] = classification.get(severity_name, 0) + 1
        return classification
    
    def _classify_by_module(self, defects: List[Defect]) -> Dict[str, int]:
        """按模块分类"""
        classification = {}
        for defect in defects:
            # 通过关联的测试用例获取模块信息
            if defect.test_case and defect.test_case.module:
                module = defect.test_case.module
                classification[module] = classification.get(module, 0) + 1
        return classification
    
    async def _classify_by_root_cause(self, defects: List[Defect]) -> Dict[str, int]:
        """按根因分类"""
        # 简化实现
        return {'代码逻辑错误': len(defects) // 2, '环境配置问题': len(defects) // 3, '其他': len(defects) // 6}
    
    def _classify_by_time_pattern(self, defects: List[Defect]) -> Dict[str, int]:
        """按时间模式分类"""
        classification = {'工作日': 0, '周末': 0}
        for defect in defects:
            if defect.created_at.weekday() < 5:
                classification['工作日'] += 1
            else:
                classification['周末'] += 1
        return classification
    
    def _classify_by_reporter(self, defects: List[Defect]) -> Dict[str, int]:
        """按报告人分类"""
        classification = {}
        for defect in defects:
            reporter_id = str(defect.reporter_id)
            classification[reporter_id] = classification.get(reporter_id, 0) + 1
        return classification
    
    def _classify_by_resolution_time(self, defects: List[Defect]) -> Dict[str, int]:
        """按解决时间分类"""
        classification = {'快速(1天内)': 0, '正常(1-3天)': 0, '较慢(3-7天)': 0, '很慢(7天以上)': 0}
        for defect in defects:
            if defect.resolved_at and defect.reported_at:
                resolution_time = (defect.resolved_at - defect.reported_at).days
                if resolution_time <= 1:
                    classification['快速(1天内)'] += 1
                elif resolution_time <= 3:
                    classification['正常(1-3天)'] += 1
                elif resolution_time <= 7:
                    classification['较慢(3-7天)'] += 1
                else:
                    classification['很慢(7天以上)'] += 1
        return classification
    
    async def _generate_classification_insights(self, classification_result: Dict[str, Any]) -> List[str]:
        """生成分类洞察"""
        insights = []
        
        # 分析缺陷类型分布
        type_dist = classification_result.get('by_type', {})
        if type_dist:
            max_type = max(type_dist.keys(), key=lambda x: type_dist[x])
            insights.append(f"最常见的缺陷类型是{max_type}，占比{type_dist[max_type]/sum(type_dist.values())*100:.1f}%")
        
        # 分析严重程度分布
        severity_dist = classification_result.get('by_severity', {})
        if severity_dist:
            critical_count = severity_dist.get('CRITICAL', 0)
            total_count = sum(severity_dist.values())
            if critical_count / total_count > 0.1:
                insights.append(f"严重缺陷比例较高({critical_count/total_count*100:.1f}%)，需要重点关注")
        
        # 分析解决时间分布
        resolution_dist = classification_result.get('by_resolution_time', {})
        if resolution_dist:
            slow_count = resolution_dist.get('很慢(7天以上)', 0)
            total_count = sum(resolution_dist.values())
            if slow_count / total_count > 0.2:
                insights.append(f"解决时间较慢的缺陷比例较高({slow_count/total_count*100:.1f}%)，建议优化处理流程")
        
        return insights