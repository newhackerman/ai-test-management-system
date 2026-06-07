#!/usr/bin/env python3
"""
AI缓存策略演示脚本

演示AI助手模块的Redis缓存策略功能，包括：
1. 基础缓存操作演示
2. 对话上下文缓存演示
3. AI响应缓存演示
4. 缓存管理器功能演示
5. 性能对比测试

运行方式:
python ai_cache_demo.py
"""

import asyncio
import time
import json
import random
from datetime import datetime
from typing import Dict, List, Any

# 导入缓存服务
from ..services.ai_cache_service import ai_cache_service, CacheKeyType
from ..services.ai_context_cache import ai_context_cache, ConversationContextCache
from ..services.ai_response_cache import ai_response_cache, CachedAIResponse
from ..services.ai_cache_manager import ai_cache_manager
from ..services.ai_assistant_service import AIProvider, AIResponse


class AICacheDemo:
    """AI缓存策略演示类"""
    
    def __init__(self):
        self.demo_data = self._prepare_demo_data()
    
    def _prepare_demo_data(self) -> Dict[str, Any]:
        """准备演示数据"""
        return {
            "users": [101, 102, 103, 104, 105],
            "conversations": [1001, 1002, 1003, 1004, 1005],
            "queries": [
                "如何编写高质量的测试用例？",
                "代码审查的最佳实践是什么？",
                "如何进行性能测试？",
                "自动化测试框架如何选择？",
                "项目管理中的风险控制方法",
                "敏捷开发的核心原则",
                "持续集成的配置步骤",
                "数据库优化的常见方法",
                "微服务架构的设计原则",
                "安全测试的关键要点"
            ],
            "ai_responses": [
                "编写高质量测试用例需要遵循SMART原则：具体、可测量、可达成、相关性强、有时限。",
                "代码审查最佳实践包括：制定明确的审查标准、使用自动化工具、保持建设性反馈。",
                "性能测试应该包括负载测试、压力测试、容量测试和稳定性测试四个方面。",
                "选择自动化测试框架时要考虑技术栈匹配、社区支持、学习成本和维护成本。",
                "项目风险控制包括风险识别、风险评估、风险应对和风险监控四个步骤。"
            ]
        }
    
    async def run_demo(self):
        """运行完整演示"""
        print("🚀 AI助手缓存策略演示开始")
        print("=" * 60)
        
        try:
            # 1. 基础缓存操作演示
            await self.demo_basic_cache_operations()
            
            # 2. 对话上下文缓存演示
            await self.demo_context_caching()
            
            # 3. AI响应缓存演示
            await self.demo_response_caching()
            
            # 4. 缓存管理器演示
            await self.demo_cache_management()
            
            # 5. 性能对比测试
            await self.demo_performance_comparison()
            
            # 6. 缓存统计信息
            await self.show_cache_statistics()
            
        except Exception as e:
            print(f"❌ 演示过程中出现错误: {str(e)}")
        
        print("\n✅ AI助手缓存策略演示完成")
        print("=" * 60)
    
    async def demo_basic_cache_operations(self):
        """演示基础缓存操作"""
        print("\n📦 1. 基础缓存操作演示")
        print("-" * 40)
        
        # 设置用户偏好缓存
        user_id = self.demo_data["users"][0]
        preferences = {
            "theme": "dark",
            "language": "zh-CN",
            "ai_model": "gpt-4",
            "response_style": "detailed"
        }
        
        print(f"设置用户 {user_id} 的偏好缓存...")
        success = await ai_cache_service.set(
            CacheKeyType.USER_PREFERENCES, 
            preferences, 
            user_id
        )
        print(f"✅ 缓存设置{'成功' if success else '失败'}")
        
        # 获取用户偏好缓存
        print(f"获取用户 {user_id} 的偏好缓存...")
        cached_preferences = await ai_cache_service.get(
            CacheKeyType.USER_PREFERENCES, 
            user_id
        )
        print(f"✅ 缓存获取: {cached_preferences}")
        
        # 批量操作演示
        print("\n批量缓存操作演示...")
        batch_data = {}
        for i, user_id in enumerate(self.demo_data["users"][:3]):
            batch_data[(user_id,)] = {
                "theme": ["light", "dark", "auto"][i],
                "language": "zh-CN",
                "last_login": datetime.utcnow().isoformat()
            }
        
        batch_count = await ai_cache_service.batch_set(
            CacheKeyType.USER_PREFERENCES, 
            batch_data
        )
        print(f"✅ 批量设置完成: {batch_count} 个用户偏好")
        
        # 批量获取
        key_args_list = [(user_id,) for user_id in self.demo_data["users"][:3]]
        batch_results = await ai_cache_service.batch_get(
            CacheKeyType.USER_PREFERENCES, 
            key_args_list
        )
        print(f"✅ 批量获取完成: {len(batch_results)} 个结果")
    
    async def demo_context_caching(self):
        """演示对话上下文缓存"""
        print("\n💬 2. 对话上下文缓存演示")
        print("-" * 40)
        
        conversation_id = self.demo_data["conversations"][0]
        user_id = self.demo_data["users"][0]
        
        # 创建对话上下文
        messages = [
            {
                "id": 1,
                "role": "USER",
                "content": "你好，我想了解测试用例编写的方法",
                "tokens_used": 25,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": 2,
                "role": "ASSISTANT", 
                "content": "你好！我很乐意帮助你了解测试用例编写。测试用例编写是软件测试的核心环节...",
                "tokens_used": 150,
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        
        context = ConversationContextCache(
            conversation_id=conversation_id,
            messages=messages,
            token_count=175,
            summary="用户咨询测试用例编写方法"
        )
        
        print(f"缓存对话上下文 (对话ID: {conversation_id})...")
        success = await ai_context_cache.set_conversation_context(context, user_id)
        print(f"✅ 上下文缓存{'成功' if success else '失败'}")
        
        # 获取对话上下文
        print("获取对话上下文...")
        cached_context = await ai_context_cache.get_conversation_context(
            conversation_id, user_id
        )
        if cached_context:
            print(f"✅ 获取成功: {len(cached_context.messages)} 条消息, "
                  f"{cached_context.token_count} tokens")
        
        # 更新对话上下文
        new_message = {
            "id": 3,
            "role": "USER",
            "content": "能给我一个具体的例子吗？",
            "tokens_used": 20,
            "created_at": datetime.utcnow().isoformat()
        }
        
        print("更新对话上下文...")
        success = await ai_context_cache.update_conversation_context(
            conversation_id, user_id, new_message
        )
        print(f"✅ 上下文更新{'成功' if success else '失败'}")
        
        # 生成AI上下文字符串
        context_str = await ai_context_cache.get_context_for_ai(
            conversation_id, user_id, max_tokens=1000
        )
        print(f"✅ AI上下文字符串长度: {len(context_str)} 字符")
    
    async def demo_response_caching(self):
        """演示AI响应缓存"""
        print("\n🤖 3. AI响应缓存演示")
        print("-" * 40)
        
        # 模拟AI响应
        queries_and_responses = [
            (
                "如何编写高质量的测试用例？",
                AIResponse(
                    content="编写高质量测试用例需要遵循SMART原则：具体、可测量、可达成、相关性强、有时限。首先要明确测试目标...",
                    provider=AIProvider.OPENAI,
                    model="gpt-4",
                    tokens_used=200,
                    confidence_score=0.92,
                    metadata={"quality": "high", "domain": "testing"}
                )
            ),
            (
                "代码审查的最佳实践是什么？",
                AIResponse(
                    content="代码审查最佳实践包括：1. 制定明确的审查标准 2. 使用自动化工具辅助 3. 保持建设性反馈...",
                    provider=AIProvider.ANTHROPIC,
                    model="claude-3-sonnet",
                    tokens_used=180,
                    confidence_score=0.89,
                    metadata={"quality": "high", "domain": "development"}
                )
            )
        ]
        
        # 缓存AI响应
        for query, response in queries_and_responses:
            print(f"缓存AI响应: {query[:30]}...")
            success = await ai_response_cache.cache_response(query, response)
            print(f"✅ 响应缓存{'成功' if success else '失败'}")
        
        # 获取缓存的响应
        test_query = queries_and_responses[0][0]
        print(f"\n获取缓存响应: {test_query[:30]}...")
        cached_response = await ai_response_cache.get_cached_response(test_query)
        
        if cached_response:
            print(f"✅ 缓存命中!")
            print(f"   提供商: {cached_response.provider}")
            print(f"   模型: {cached_response.model}")
            print(f"   质量分数: {cached_response.quality_score:.2f}")
            print(f"   命中次数: {cached_response.hit_count}")
        else:
            print("❌ 缓存未命中")
        
        # 测试相似查询匹配
        similar_query = "怎样编写好的测试用例？"
        print(f"\n测试相似查询: {similar_query}")
        similar_response = await ai_response_cache.get_cached_response(similar_query)
        
        if similar_response:
            print("✅ 相似查询匹配成功!")
            print(f"   原始查询: {similar_response.metadata.get('original_query', '')[:30]}...")
        else:
            print("❌ 相似查询未匹配")
    
    async def demo_cache_management(self):
        """演示缓存管理器功能"""
        print("\n🔧 4. 缓存管理器演示")
        print("-" * 40)
        
        # 初始化缓存管理器
        print("初始化缓存管理器...")
        success = await ai_cache_manager.initialize()
        print(f"✅ 初始化{'成功' if success else '失败'}")
        
        # 获取缓存健康状况
        print("\n检查缓存健康状况...")
        health_report = await ai_cache_manager.get_overall_health()
        print(f"✅ 健康状态: {health_report.status.value}")
        print(f"   命中率: {health_report.hit_rate:.2%}")
        print(f"   内存使用: {health_report.memory_usage:.2%}")
        print(f"   响应时间: {health_report.response_time:.3f}s")
        
        if health_report.recommendations:
            print("   建议:")
            for rec in health_report.recommendations:
                print(f"   - {rec}")
        
        # 性能优化
        print("\n执行性能优化...")
        optimization_results = await ai_cache_manager.optimize_cache_performance()
        print(f"✅ 优化完成: {len(optimization_results['actions_taken'])} 个操作")
        for action in optimization_results['actions_taken']:
            print(f"   - {action}")
        
        # 获取仪表板数据
        print("\n获取缓存仪表板数据...")
        dashboard_data = await ai_cache_manager.get_cache_dashboard_data()
        print("✅ 仪表板数据获取成功")
        print(f"   监控的缓存类型: {len(dashboard_data.get('detailed_metrics', {}))}")
        print(f"   系统信息: {len(dashboard_data.get('system_info', {}))}")
    
    async def demo_performance_comparison(self):
        """演示性能对比测试"""
        print("\n⚡ 5. 性能对比测试")
        print("-" * 40)
        
        # 准备测试数据
        test_queries = self.demo_data["queries"][:5]
        test_responses = []
        
        for i, query in enumerate(test_queries):
            response = AIResponse(
                content=self.demo_data["ai_responses"][i % len(self.demo_data["ai_responses"])],
                provider=AIProvider.OPENAI,
                model="gpt-4",
                tokens_used=random.randint(100, 300),
                confidence_score=random.uniform(0.8, 0.95)
            )
            test_responses.append((query, response))
        
        # 首次调用（缓存未命中）
        print("测试首次调用性能（缓存未命中）...")
        miss_times = []
        
        for query, response in test_responses:
            start_time = time.time()
            
            # 模拟AI服务调用延迟
            await asyncio.sleep(0.1)  # 模拟100ms延迟
            
            # 缓存响应
            await ai_response_cache.cache_response(query, response)
            
            end_time = time.time()
            miss_times.append(end_time - start_time)
        
        avg_miss_time = sum(miss_times) / len(miss_times)
        print(f"✅ 平均响应时间（未命中）: {avg_miss_time:.3f}s")
        
        # 第二次调用（缓存命中）
        print("\n测试缓存命中性能...")
        hit_times = []
        
        for query, _ in test_responses:
            start_time = time.time()
            
            # 从缓存获取响应
            cached_response = await ai_response_cache.get_cached_response(query)
            
            end_time = time.time()
            hit_times.append(end_time - start_time)
        
        avg_hit_time = sum(hit_times) / len(hit_times)
        print(f"✅ 平均响应时间（命中）: {avg_hit_time:.3f}s")
        
        # 性能提升计算
        improvement = ((avg_miss_time - avg_hit_time) / avg_miss_time) * 100
        print(f"🚀 性能提升: {improvement:.1f}%")
        
        # 批量操作性能测试
        print("\n测试批量操作性能...")
        batch_data = {(f"query_{i}",): f"response_{i}" for i in range(100)}
        
        start_time = time.time()
        batch_count = await ai_cache_service.batch_set(CacheKeyType.AI_RESPONSE, batch_data)
        end_time = time.time()
        
        batch_time = end_time - start_time
        print(f"✅ 批量设置 {batch_count} 项耗时: {batch_time:.3f}s")
        print(f"   平均每项: {(batch_time / batch_count * 1000):.2f}ms")
    
    async def show_cache_statistics(self):
        """显示缓存统计信息"""
        print("\n📊 6. 缓存统计信息")
        print("-" * 40)
        
        # 获取各类缓存的指标
        all_metrics = ai_cache_service.get_metrics()
        
        print("缓存类型统计:")
        for cache_type, metrics in all_metrics.items():
            if metrics.hits + metrics.misses > 0:
                print(f"  {cache_type}:")
                print(f"    命中率: {metrics.hit_rate:.2%}")
                print(f"    总操作: {metrics.hits + metrics.misses + metrics.sets + metrics.deletes}")
                print(f"    平均响应时间: {metrics.avg_access_time:.3f}s")
        
        # 获取响应缓存统计
        response_stats = await ai_response_cache.get_cache_statistics()
        if response_stats:
            print(f"\nAI响应缓存统计:")
            print(f"  总缓存响应数: {response_stats.get('total_cached_responses', 0)}")
            print(f"  估算成本节省: ${response_stats.get('estimated_cost_saved_usd', 0):.2f}")
        
        # 获取缓存信息
        cache_info = ai_cache_service.get_cache_info()
        print(f"\n系统信息:")
        print(f"  L1缓存大小: {cache_info.get('l1_cache_size', 0)}")
        print(f"  Redis连接状态: {'正常' if cache_info.get('redis_connected', False) else '异常'}")
    
    def print_separator(self, title: str):
        """打印分隔符"""
        print(f"\n{'='*20} {title} {'='*20}")


async def main():
    """主函数"""
    demo = AICacheDemo()
    await demo.run_demo()


if __name__ == "__main__":
    # 运行演示
    print("AI助手缓存策略演示")
    print("请确保Redis服务正在运行...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"演示运行出错: {str(e)}")
        import traceback
        traceback.print_exc()