"""
AI响应缓存服务

专门处理AI响应的缓存策略，包括：
1. 查询响应缓存 - 避免重复调用AI服务
2. 智能去重 - 相似查询的响应复用
3. 响应质量评估 - 只缓存高质量响应
4. 成本优化 - 减少AI API调用成本
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .ai_cache_service import ai_cache_service, CacheKeyType, cache_result
from ..services.ai_assistant_service import AIProvider, AIResponse

logger = logging.getLogger(__name__)


class ResponseQuality(Enum):
    """响应质量等级"""
    EXCELLENT = "excellent"  # 优秀 - 长期缓存
    GOOD = "good"           # 良好 - 中期缓存
    AVERAGE = "average"     # 一般 - 短期缓存
    POOR = "poor"          # 较差 - 不缓存


@dataclass
class CachedAIResponse:
    """缓存的AI响应对象"""
    query_hash: str                    # 查询哈希
    response_content: str              # 响应内容
    provider: str                      # AI提供商
    model: str                        # 使用的模型
    tokens_used: int                  # 使用的token数
    confidence_score: float           # 置信度分数
    quality_score: float              # 质量分数
    created_at: str                   # 创建时间
    hit_count: int = 0                # 命中次数
    last_accessed: Optional[str] = None  # 最后访问时间
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


class AIResponseCacheService:
    """AI响应缓存服务"""
    
    def __init__(self):
        self.cache = ai_cache_service
        self.similarity_threshold = 0.3   # 相似度阈值（降低以便更好地匹配相似查询）
        self.min_quality_score = 0.6     # 最低质量分数
        self.max_cache_size = 10000      # 最大缓存条数
    
    def _generate_query_hash(self, query: str, context: Optional[Dict] = None,
                           provider: Optional[str] = None) -> str:
        """
        生成查询哈希
        
        Args:
            query: 查询内容
            context: 上下文信息
            provider: AI提供商
            
        Returns:
            str: 查询哈希
        """
        # 标准化查询内容
        normalized_query = query.strip().lower()
        
        # 构建哈希输入
        hash_input = normalized_query
        
        if context:
            # 只包含重要的上下文信息
            important_context = {
                k: v for k, v in context.items() 
                if k in ['user_id', 'conversation_type', 'domain', 'language']
            }
            if important_context:
                hash_input += json.dumps(important_context, sort_keys=True)
        
        if provider:
            hash_input += provider
        
        # 生成MD5哈希
        return hashlib.md5(hash_input.encode('utf-8')).hexdigest()
    
    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """
        计算查询相似度（改进实现，支持中英文）
        
        Args:
            query1: 查询1
            query2: 查询2
            
        Returns:
            float: 相似度分数 (0-1)
        """
        try:
            # 标准化查询
            q1 = query1.lower().strip()
            q2 = query2.lower().strip()
            
            if not q1 or not q2:
                return 0.0
            
            # 如果查询完全相同
            if q1 == q2:
                return 1.0
            
            # 方法1: 基于词汇重叠的相似度（适用于英文和中文词汇）
            words1 = set(q1.split())
            words2 = set(q2.split())
            
            word_similarity = 0.0
            if words1 and words2:
                intersection = words1.intersection(words2)
                union = words1.union(words2)
                word_similarity = len(intersection) / len(union) if union else 0.0
            
            # 方法2: 基于字符n-gram的相似度（适用于中文）
            def get_ngrams(text: str, n: int = 2) -> set:
                """获取n-gram集合"""
                if len(text) < n:
                    return {text}
                return {text[i:i+n] for i in range(len(text) - n + 1)}
            
            # 2-gram相似度
            ngrams1 = get_ngrams(q1.replace(' ', ''), 2)
            ngrams2 = get_ngrams(q2.replace(' ', ''), 2)
            
            ngram_similarity = 0.0
            if ngrams1 and ngrams2:
                intersection = ngrams1.intersection(ngrams2)
                union = ngrams1.union(ngrams2)
                ngram_similarity = len(intersection) / len(union) if union else 0.0
            
            # 方法3: 基于关键词匹配的相似度
            # 定义一些关键词组
            keywords_groups = [
                ['测试', '用例', 'test', 'case'],
                ['编写', '写', 'write', 'create'],
                ['质量', '好', 'quality', 'good'],
                ['如何', '怎么', '怎样', 'how', 'what'],
                ['验证', '检验', 'verify', 'validate'],
                ['缓存', 'cache', '缓冲'],
                ['功能', 'function', 'feature'],
                ['机器学习', 'machine learning', 'ml'],
                ['代码', 'code', 'programming'],
                ['审查', 'review', 'check']
            ]
            
            keyword_matches = 0
            total_keywords = 0
            
            for group in keywords_groups:
                q1_has_keyword = any(keyword in q1 for keyword in group)
                q2_has_keyword = any(keyword in q2 for keyword in group)
                
                if q1_has_keyword or q2_has_keyword:
                    total_keywords += 1
                    if q1_has_keyword and q2_has_keyword:
                        keyword_matches += 1
            
            keyword_similarity = keyword_matches / total_keywords if total_keywords > 0 else 0.0
            
            # 综合相似度计算（加权平均）
            final_similarity = (
                word_similarity * 0.4 +      # 词汇相似度权重40%
                ngram_similarity * 0.4 +     # n-gram相似度权重40%
                keyword_similarity * 0.2     # 关键词相似度权重20%
            )
            
            # 调试日志
            if final_similarity > 0.1:  # 只记录有一定相似度的查询
                logger.debug(f"Query similarity: '{q1}' vs '{q2}' = {final_similarity:.3f} "
                           f"(word: {word_similarity:.3f}, ngram: {ngram_similarity:.3f}, keyword: {keyword_similarity:.3f})")
            
            return min(final_similarity, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating query similarity: {str(e)}")
            return 0.0
    
    def _evaluate_response_quality(self, response: AIResponse, query: str) -> float:
        """
        评估响应质量
        
        Args:
            response: AI响应
            query: 原始查询
            
        Returns:
            float: 质量分数 (0-1)
        """
        try:
            quality_factors = []
            
            # 1. 置信度分数
            quality_factors.append(response.confidence_score)
            
            # 2. 响应长度合理性
            response_length = len(response.content)
            query_length = len(query)
            
            if response_length < query_length * 0.5:
                length_score = 0.3  # 响应太短
            elif response_length > query_length * 10:
                length_score = 0.7  # 响应可能太长
            else:
                length_score = 1.0  # 长度合理
            
            quality_factors.append(length_score)
            
            # 3. 内容质量检查
            content_score = 1.0
            
            # 检查是否包含错误信息
            error_indicators = ['抱歉', '无法', '不知道', '错误', '失败']
            if any(indicator in response.content for indicator in error_indicators):
                content_score *= 0.5
            
            # 检查是否包含有用信息
            useful_indicators = ['建议', '方法', '步骤', '解决', '分析']
            if any(indicator in response.content for indicator in useful_indicators):
                content_score *= 1.2
            
            content_score = min(content_score, 1.0)
            quality_factors.append(content_score)
            
            # 4. 提供商可靠性
            provider_scores = {
                AIProvider.OPENAI.value: 0.95,
                AIProvider.ANTHROPIC.value: 0.93,
                AIProvider.GOOGLE_GEMINI.value: 0.90,
                AIProvider.BAIDU_WENXIN.value: 0.85,
                AIProvider.ALIYUN_TONGYI.value: 0.82
            }
            
            provider_score = provider_scores.get(response.provider.value, 0.8)
            quality_factors.append(provider_score)
            
            # 计算综合质量分数
            return sum(quality_factors) / len(quality_factors)
            
        except Exception as e:
            logger.error(f"Error evaluating response quality: {str(e)}")
            return 0.5  # 默认中等质量
    
    def _determine_cache_ttl(self, quality_score: float, provider: str) -> int:
        """
        根据质量分数确定缓存TTL
        
        Args:
            quality_score: 质量分数
            provider: AI提供商
            
        Returns:
            int: TTL（秒）
        """
        base_ttl = 3600  # 1小时基础TTL
        
        # 根据质量调整TTL
        if quality_score >= 0.9:
            ttl_multiplier = 24  # 24小时
        elif quality_score >= 0.8:
            ttl_multiplier = 12  # 12小时
        elif quality_score >= 0.7:
            ttl_multiplier = 6   # 6小时
        elif quality_score >= 0.6:
            ttl_multiplier = 2   # 2小时
        else:
            return 0  # 不缓存低质量响应
        
        # 根据提供商调整（成本考虑）
        provider_multipliers = {
            AIProvider.OPENAI.value: 1.5,      # 成本高，缓存时间长
            AIProvider.ANTHROPIC.value: 1.3,
            AIProvider.GOOGLE_GEMINI.value: 1.0,
            AIProvider.BAIDU_WENXIN.value: 0.8,
            AIProvider.ALIYUN_TONGYI.value: 0.7
        }
        
        provider_multiplier = provider_multipliers.get(provider, 1.0)
        
        return int(base_ttl * ttl_multiplier * provider_multiplier)
    
    async def get_cached_response(self, query: str, context: Optional[Dict] = None,
                                provider: Optional[str] = None) -> Optional[CachedAIResponse]:
        """
        获取缓存的AI响应
        
        Args:
            query: 查询内容
            context: 上下文信息
            provider: AI提供商
            
        Returns:
            Optional[CachedAIResponse]: 缓存的响应，如果不存在返回None
        """
        try:
            # 生成查询哈希
            query_hash = self._generate_query_hash(query, context, provider)
            
            # 尝试精确匹配
            cached_data = await self.cache.get(CacheKeyType.AI_RESPONSE, query_hash)
            
            if cached_data:
                cached_response = CachedAIResponse(**cached_data)
                
                # 更新访问统计
                cached_response.hit_count += 1
                cached_response.last_accessed = datetime.utcnow().isoformat()
                
                # 异步更新缓存中的统计信息
                await self._update_response_stats(cached_response)
                
                logger.debug(f"Cache hit for query hash: {query_hash}")
                return cached_response
            
            # 尝试相似查询匹配
            similar_response = await self._find_similar_cached_response(query, context, provider)
            if similar_response:
                logger.debug(f"Similar cache hit for query: {query[:50]}...")
                return similar_response
            
            logger.debug(f"Cache miss for query: {query[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached response: {str(e)}")
            return None
    
    async def cache_response(self, query: str, response: AIResponse,
                           context: Optional[Dict] = None) -> bool:
        """
        缓存AI响应
        
        Args:
            query: 原始查询
            response: AI响应
            context: 上下文信息
            
        Returns:
            bool: 是否缓存成功
        """
        try:
            # 评估响应质量
            quality_score = self._evaluate_response_quality(response, query)
            
            # 检查是否达到缓存质量要求
            if quality_score < self.min_quality_score:
                logger.debug(f"Response quality too low to cache: {quality_score}")
                return False
            
            # 生成查询哈希
            query_hash = self._generate_query_hash(query, context, response.provider.value)
            
            # 创建缓存对象
            cached_response = CachedAIResponse(
                query_hash=query_hash,
                response_content=response.content,
                provider=response.provider.value,
                model=response.model,
                tokens_used=response.tokens_used,
                confidence_score=response.confidence_score,
                quality_score=quality_score,
                created_at=datetime.utcnow().isoformat(),
                metadata={
                    "original_query": query[:200],  # 只保存前200字符
                    "context_keys": list(context.keys()) if context else [],
                    **response.metadata
                }
            )
            
            # 确定缓存TTL
            ttl = self._determine_cache_ttl(quality_score, response.provider.value)
            
            if ttl <= 0:
                logger.debug("Response quality insufficient for caching")
                return False
            
            # 转换为字典
            cache_data = {
                "query_hash": cached_response.query_hash,
                "response_content": cached_response.response_content,
                "provider": cached_response.provider,
                "model": cached_response.model,
                "tokens_used": cached_response.tokens_used,
                "confidence_score": cached_response.confidence_score,
                "quality_score": cached_response.quality_score,
                "created_at": cached_response.created_at,
                "hit_count": cached_response.hit_count,
                "last_accessed": cached_response.last_accessed,
                "metadata": cached_response.metadata
            }
            
            # 缓存响应
            success = await self.cache.set(
                CacheKeyType.AI_RESPONSE,
                cache_data,
                query_hash,
                ttl=ttl
            )
            
            if success:
                logger.debug(f"Cached AI response: {query_hash}, TTL: {ttl}s, Quality: {quality_score:.2f}")
                
                # 更新缓存统计
                await self._update_cache_statistics(response.provider.value, quality_score)
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching AI response: {str(e)}")
            return False
    
    async def _find_similar_cached_response(self, query: str, context: Optional[Dict] = None,
                                          provider: Optional[str] = None) -> Optional[CachedAIResponse]:
        """
        查找相似的缓存响应
        
        Args:
            query: 查询内容
            context: 上下文信息
            provider: AI提供商
            
        Returns:
            Optional[CachedAIResponse]: 相似的缓存响应
        """
        try:
            # 获取所有AI响应缓存键
            pattern = f"ai_assistant:{CacheKeyType.AI_RESPONSE.value}:*"
            cache_keys = self.cache.redis.keys(pattern)
            
            if not cache_keys:
                return None
            
            # 限制检查数量以避免性能问题
            max_check = min(100, len(cache_keys))
            
            best_similarity = 0.0
            best_response = None
            
            for i, cache_key in enumerate(cache_keys[:max_check]):
                try:
                    cached_data = self.cache.redis.get(cache_key)
                    if not cached_data:
                        continue
                    
                    cached_response = CachedAIResponse(**cached_data)
                    
                    # 检查提供商匹配
                    if provider and cached_response.provider != provider:
                        continue
                    
                    # 计算查询相似度
                    original_query = cached_response.metadata.get('original_query', '')
                    similarity = self._calculate_query_similarity(query, original_query)
                    
                    # 如果相似度足够高且比当前最佳更好
                    if similarity >= self.similarity_threshold and similarity > best_similarity:
                        best_similarity = similarity
                        best_response = cached_response
                
                except Exception as e:
                    logger.warning(f"Error checking cached response {cache_key}: {str(e)}")
                    continue
            
            if best_response:
                # 更新访问统计
                best_response.hit_count += 1
                best_response.last_accessed = datetime.utcnow().isoformat()
                await self._update_response_stats(best_response)
                
                logger.debug(f"Found similar cached response with similarity: {best_similarity:.2f}")
            
            return best_response
            
        except Exception as e:
            logger.error(f"Error finding similar cached response: {str(e)}")
            return None
    
    async def _update_response_stats(self, cached_response: CachedAIResponse):
        """更新响应统计信息"""
        try:
            # 异步更新缓存中的统计信息
            cache_data = {
                "query_hash": cached_response.query_hash,
                "response_content": cached_response.response_content,
                "provider": cached_response.provider,
                "model": cached_response.model,
                "tokens_used": cached_response.tokens_used,
                "confidence_score": cached_response.confidence_score,
                "quality_score": cached_response.quality_score,
                "created_at": cached_response.created_at,
                "hit_count": cached_response.hit_count,
                "last_accessed": cached_response.last_accessed,
                "metadata": cached_response.metadata
            }
            
            await self.cache.set(
                CacheKeyType.AI_RESPONSE,
                cache_data,
                cached_response.query_hash
            )
            
        except Exception as e:
            logger.error(f"Error updating response stats: {str(e)}")
    
    async def _update_cache_statistics(self, provider: str, quality_score: float):
        """更新缓存统计信息"""
        try:
            stats_key = f"cache_stats_{provider}"
            
            # 获取现有统计
            existing_stats = await self.cache.get(CacheKeyType.USAGE_STATS, stats_key) or {
                "total_cached": 0,
                "avg_quality": 0.0,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # 更新统计
            total_cached = existing_stats["total_cached"] + 1
            current_avg = existing_stats["avg_quality"]
            new_avg = (current_avg * (total_cached - 1) + quality_score) / total_cached
            
            updated_stats = {
                "total_cached": total_cached,
                "avg_quality": new_avg,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # 保存更新的统计
            await self.cache.set(CacheKeyType.USAGE_STATS, updated_stats, stats_key, ttl=86400)
            
        except Exception as e:
            logger.error(f"Error updating cache statistics: {str(e)}")
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            # 获取基础指标
            metrics = self.cache.get_metrics(CacheKeyType.AI_RESPONSE)
            
            # 获取各提供商统计
            provider_stats = {}
            for provider in AIProvider:
                stats_key = f"cache_stats_{provider.value}"
                stats = await self.cache.get(CacheKeyType.USAGE_STATS, stats_key)
                if stats:
                    provider_stats[provider.value] = stats
            
            # 计算成本节省
            total_cached_responses = sum(
                stats.get("total_cached", 0) for stats in provider_stats.values()
            )
            
            # 估算成本节省（基于平均token成本）
            avg_tokens_per_response = 500
            avg_cost_per_1k_tokens = 0.02
            estimated_cost_saved = (total_cached_responses * avg_tokens_per_response * avg_cost_per_1k_tokens) / 1000
            
            return {
                "cache_metrics": metrics,
                "provider_statistics": provider_stats,
                "total_cached_responses": total_cached_responses,
                "estimated_cost_saved_usd": round(estimated_cost_saved, 2),
                "similarity_threshold": self.similarity_threshold,
                "min_quality_score": self.min_quality_score,
                "cache_config": {
                    "max_cache_size": self.max_cache_size,
                    "ttl_strategy": "quality_based"
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cache statistics: {str(e)}")
            return {}
    
    async def cleanup_low_quality_cache(self, min_quality: float = 0.5) -> int:
        """
        清理低质量缓存
        
        Args:
            min_quality: 最低质量阈值
            
        Returns:
            int: 清理的缓存数量
        """
        try:
            pattern = f"ai_assistant:{CacheKeyType.AI_RESPONSE.value}:*"
            cache_keys = self.cache.redis.keys(pattern)
            
            cleaned_count = 0
            
            for cache_key in cache_keys:
                try:
                    cached_data = self.cache.redis.get(cache_key)
                    if not cached_data:
                        continue
                    
                    cached_response = CachedAIResponse(**cached_data)
                    
                    # 检查质量分数
                    if cached_response.quality_score < min_quality:
                        if self.cache.redis.delete(cache_key):
                            cleaned_count += 1
                
                except Exception as e:
                    logger.warning(f"Error checking cache entry {cache_key}: {str(e)}")
                    continue
            
            logger.info(f"Cleaned up {cleaned_count} low-quality cache entries")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up low-quality cache: {str(e)}")
            return 0
    
    async def preload_common_responses(self, common_queries: List[Dict[str, Any]]) -> int:
        """
        预加载常见查询的响应
        
        Args:
            common_queries: 常见查询列表，每个包含query和context
            
        Returns:
            int: 预加载的响应数量
        """
        try:
            preloaded_count = 0
            
            for query_info in common_queries:
                query = query_info.get('query', '')
                context = query_info.get('context', {})
                
                if not query:
                    continue
                
                # 检查是否已经缓存
                existing_response = await self.get_cached_response(query, context)
                if existing_response:
                    continue
                
                # 这里应该调用AI服务获取响应，然后缓存
                # 由于这是缓存服务，我们只是标记为需要预加载
                logger.debug(f"Marked for preloading: {query[:50]}...")
                preloaded_count += 1
            
            logger.info(f"Marked {preloaded_count} queries for preloading")
            return preloaded_count
            
        except Exception as e:
            logger.error(f"Error preloading common responses: {str(e)}")
            return 0
    
    async def invalidate_cache_by_pattern(self, pattern: str) -> int:
        """
        根据模式失效缓存
        
        Args:
            pattern: 匹配模式，如 "user_123_*"
            
        Returns:
            int: 失效的缓存数量
        """
        try:
            cache_pattern = f"ai_assistant:{CacheKeyType.AI_RESPONSE.value}:{pattern}"
            return await self.cache.clear_pattern(CacheKeyType.AI_RESPONSE, pattern)
            
        except Exception as e:
            logger.error(f"Error invalidating cache by pattern {pattern}: {str(e)}")
            return 0
    
    async def get_cache_size_info(self) -> Dict[str, Any]:
        """
        获取缓存大小信息
        
        Returns:
            Dict[str, Any]: 缓存大小信息
        """
        try:
            # 获取所有AI响应缓存键
            pattern = f"ai_assistant:{CacheKeyType.AI_RESPONSE.value}:*"
            cache_keys = self.cache.redis.keys(pattern)
            
            total_entries = len(cache_keys)
            total_size_bytes = 0
            
            # 估算总大小（采样方式）
            sample_size = min(100, total_entries)
            if sample_size > 0:
                sample_keys = cache_keys[:sample_size]
                sample_total_size = 0
                
                for key in sample_keys:
                    try:
                        cached_data = self.cache.redis.get(key)
                        if cached_data:
                            # 估算数据大小
                            data_str = json.dumps(cached_data) if isinstance(cached_data, dict) else str(cached_data)
                            sample_total_size += len(data_str.encode('utf-8'))
                    except Exception:
                        continue
                
                # 根据采样估算总大小
                if sample_size > 0:
                    avg_size = sample_total_size / sample_size
                    total_size_bytes = int(avg_size * total_entries)
            
            return {
                "total_entries": total_entries,
                "estimated_size_bytes": total_size_bytes,
                "estimated_size_mb": round(total_size_bytes / (1024 * 1024), 2),
                "sample_size": sample_size,
                "max_cache_size": self.max_cache_size
            }
            
        except Exception as e:
            logger.error(f"Error getting cache size info: {str(e)}")
            return {"error": str(e)}
    
    async def export_cache_data(self, output_format: str = "json") -> Dict[str, Any]:
        """
        导出缓存数据
        
        Args:
            output_format: 输出格式 ("json", "csv")
            
        Returns:
            Dict[str, Any]: 导出结果
        """
        try:
            pattern = f"ai_assistant:{CacheKeyType.AI_RESPONSE.value}:*"
            cache_keys = self.cache.redis.keys(pattern)
            
            exported_data = []
            
            for cache_key in cache_keys:
                try:
                    cached_data = self.cache.redis.get(cache_key)
                    if cached_data:
                        export_item = {
                            "cache_key": cache_key,
                            "query_hash": cached_data.get("query_hash", ""),
                            "provider": cached_data.get("provider", ""),
                            "model": cached_data.get("model", ""),
                            "quality_score": cached_data.get("quality_score", 0.0),
                            "hit_count": cached_data.get("hit_count", 0),
                            "created_at": cached_data.get("created_at", ""),
                            "last_accessed": cached_data.get("last_accessed", ""),
                            "response_length": len(cached_data.get("response_content", "")),
                            "tokens_used": cached_data.get("tokens_used", 0)
                        }
                        exported_data.append(export_item)
                        
                except Exception as e:
                    logger.warning(f"Error exporting cache entry {cache_key}: {str(e)}")
                    continue
            
            return {
                "format": output_format,
                "total_entries": len(exported_data),
                "data": exported_data,
                "exported_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error exporting cache data: {str(e)}")
            return {"error": str(e)}
    
    async def analyze_cache_performance(self) -> Dict[str, Any]:
        """
        分析缓存性能
        
        Returns:
            Dict[str, Any]: 性能分析结果
        """
        try:
            # 获取缓存统计
            stats = await self.get_cache_statistics()
            
            # 分析命中率
            cache_metrics = stats.get("cache_metrics", {}).get("ai_resp")
            if cache_metrics:
                hit_rate = cache_metrics.hit_rate
                total_requests = cache_metrics.hits + cache_metrics.misses
                avg_response_time = cache_metrics.avg_access_time
            else:
                hit_rate = 0.0
                total_requests = 0
                avg_response_time = 0.0
            
            # 分析提供商分布
            provider_stats = stats.get("provider_statistics", {})
            provider_distribution = {}
            total_cached = 0
            
            for provider, provider_stat in provider_stats.items():
                cached_count = provider_stat.get("total_cached", 0)
                provider_distribution[provider] = cached_count
                total_cached += cached_count
            
            # 计算性能评级
            performance_grade = "A"
            if hit_rate < 0.6:
                performance_grade = "C"
            elif hit_rate < 0.8:
                performance_grade = "B"
            
            # 生成优化建议
            recommendations = []
            
            if hit_rate < 0.6:
                recommendations.append("缓存命中率较低，建议增加预热常见查询")
            
            if avg_response_time > 0.1:
                recommendations.append("缓存响应时间较慢，建议优化缓存键设计")
            
            if total_cached < 100:
                recommendations.append("缓存数据量较少，建议增加缓存策略覆盖范围")
            
            return {
                "performance_grade": performance_grade,
                "hit_rate": hit_rate,
                "total_requests": total_requests,
                "avg_response_time": avg_response_time,
                "total_cached_responses": total_cached,
                "provider_distribution": provider_distribution,
                "recommendations": recommendations,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing cache performance: {str(e)}")
            return {"error": str(e)}


# 创建全局AI响应缓存服务实例
ai_response_cache = AIResponseCacheService()