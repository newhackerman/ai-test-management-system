#!/usr/bin/env python3
"""
AI助手对话上下文缓存功能演示

本演示展示了AI助手模块的对话上下文缓存功能，包括：
1. 对话上下文的存储和检索
2. 智能上下文压缩
3. 上下文摘要生成
4. 活跃对话管理
5. 缓存性能监控

使用场景：
- 快速恢复用户对话状态
- 智能管理长对话的上下文
- 优化AI模型的上下文输入
- 提升用户体验和系统性能
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 模拟导入（实际使用时需要正确的导入路径）
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.ai_context_cache import AIContextCacheService, ConversationContextCache
from services.ai_cache_service import CacheKeyType


class ContextCacheDemo:
    """对话上下文缓存演示类"""
    
    def __init__(self):
        self.context_cache = AIContextCacheService()
        self.demo_conversations = {}
    
    async def run_demo(self):
        """运行完整演示"""
        print("🚀 AI助手对话上下文缓存功能演示")
        print("=" * 60)
        
        # 演示1: 基础对话上下文缓存
        await self.demo_basic_context_caching()
        
        # 演示2: 对话上下文更新
        await self.demo_context_updates()
        
        # 演示3: 智能上下文压缩
        await self.demo_context_compression()
        
        # 演示4: AI上下文生成
        await self.demo_ai_context_generation()
        
        # 演示5: 活跃对话管理
        await self.demo_active_conversations()
        
        # 演示6: 缓存性能监控
        await self.demo_cache_monitoring()
        
        print("\n🎉 演示完成！")
        print("=" * 60)
    
    async def demo_basic_context_caching(self):
        """演示基础对话上下文缓存"""
        print("\n📝 演示1: 基础对话上下文缓存")
        print("-" * 40)
        
        # 创建测试对话
        conversation_id = 1001
        user_id = 2001
        
        # 模拟对话消息
        messages = [
            {
                "id": 1,
                "role": "USER",
                "content": "你好，我想学习Python编程",
                "tokens_used": 12,
                "created_at": datetime.now().isoformat(),
                "metadata": {"intent": "greeting"}
            },
            {
                "id": 2,
                "role": "ASSISTANT",
                "content": "你好！很高兴帮助你学习Python。Python是一门非常适合初学者的编程语言，语法简洁易懂。你想从哪个方面开始学习呢？",
                "tokens_used": 35,
                "created_at": datetime.now().isoformat(),
                "confidence_score": 0.95,
                "metadata": {"response_type": "educational"}
            },
            {
                "id": 3,
                "role": "USER", 
                "content": "我想了解Python的基础语法",
                "tokens_used": 10,
                "created_at": datetime.now().isoformat(),
                "metadata": {"intent": "learning_request"}
            }
        ]
        
        # 创建对话上下文
        context = ConversationContextCache(
            conversation_id=conversation_id,
            messages=messages,
            token_count=sum(msg["tokens_used"] for msg in messages),
            summary=None,
            compression_applied=False
        )
        
        print(f"创建对话上下文:")
        print(f"  对话ID: {conversation_id}")
        print(f"  用户ID: {user_id}")
        print(f"  消息数量: {len(messages)}")
        print(f"  总Token数: {context.token_count}")
        
        # 模拟缓存操作
        from unittest.mock import patch
        
        with patch.object(self.context_cache.cache, 'set', return_value=True) as mock_set:
            # 设置缓存
            success = await self.context_cache.set_conversation_context(context, user_id)
            print(f"  缓存设置: {'✅ 成功' if success else '❌ 失败'}")
            
            # 验证缓存调用
            if mock_set.called:
                call_args = mock_set.call_args
                print(f"  缓存键类型: {call_args[0][0].value}")
                print(f"  缓存数据包含: {list(call_args[0][1].keys())}")
        
        # 模拟获取缓存
        cached_data = {
            "conversation_id": conversation_id,
            "messages": messages,
            "summary": None,
            "token_count": context.token_count,
            "last_updated": datetime.now().isoformat(),
            "compression_applied": False
        }
        
        with patch.object(self.context_cache.cache, 'get', return_value=cached_data):
            retrieved_context = await self.context_cache.get_conversation_context(conversation_id, user_id)
            
            if retrieved_context:
                print(f"  缓存检索: ✅ 成功")
                print(f"  检索到消息数: {len(retrieved_context.messages)}")
                print(f"  数据完整性: {'✅ 正确' if retrieved_context.token_count == context.token_count else '❌ 错误'}")
            else:
                print(f"  缓存检索: ❌ 失败")
        
        # 保存到演示数据
        self.demo_conversations[conversation_id] = context
    
    async def demo_context_updates(self):
        """演示对话上下文更新"""
        print("\n🔄 演示2: 对话上下文更新")
        print("-" * 40)
        
        conversation_id = 1001
        user_id = 2001
        
        # 获取之前的对话上下文
        existing_context = self.demo_conversations.get(conversation_id)
        if not existing_context:
            print("❌ 未找到现有对话上下文")
            return
        
        print(f"当前对话状态:")
        print(f"  消息数量: {len(existing_context.messages)}")
        print(f"  Token数量: {existing_context.token_count}")
        
        # 添加新消息
        new_messages = [
            {
                "id": 4,
                "role": "ASSISTANT",
                "content": "Python的基础语法包括变量定义、数据类型、控制结构等。让我为你详细介绍：\n\n1. 变量定义：name = 'Python'\n2. 数据类型：整数、字符串、列表等\n3. 控制结构：if语句、for循环等",
                "tokens_used": 45,
                "created_at": datetime.now().isoformat(),
                "confidence_score": 0.92,
                "metadata": {"response_type": "educational", "topic": "syntax"}
            },
            {
                "id": 5,
                "role": "USER",
                "content": "能给我一个具体的代码示例吗？",
                "tokens_used": 12,
                "created_at": datetime.now().isoformat(),
                "metadata": {"intent": "example_request"}
            }
        ]
        
        # 模拟上下文更新
        with patch.object(self.context_cache, 'get_conversation_context', return_value=existing_context), \
             patch.object(self.context_cache, 'set_conversation_context', return_value=True):
            
            for new_message in new_messages:
                print(f"\n添加新消息:")
                print(f"  角色: {new_message['role']}")
                print(f"  内容: {new_message['content'][:50]}...")
                print(f"  Token数: {new_message['tokens_used']}")
                
                success = await self.context_cache.update_conversation_context(
                    conversation_id, user_id, new_message
                )
                
                if success:
                    # 更新本地演示数据
                    existing_context.messages.append(new_message)
                    existing_context.token_count += new_message['tokens_used']
                    print(f"  更新结果: ✅ 成功")
                else:
                    print(f"  更新结果: ❌ 失败")
        
        print(f"\n更新后对话状态:")
        print(f"  消息数量: {len(existing_context.messages)}")
        print(f"  Token数量: {existing_context.token_count}")
    
    async def demo_context_compression(self):
        """演示智能上下文压缩"""
        print("\n🗜️ 演示3: 智能上下文压缩")
        print("-" * 40)
        
        # 创建需要压缩的长对话
        long_conversation_id = 1002
        user_id = 2001
        
        # 生成大量消息
        messages = []
        for i in range(1, 51):  # 50条消息
            if i % 2 == 1:  # 用户消息
                messages.append({
                    "id": i,
                    "role": "USER",
                    "content": f"这是第{i}条用户消息。我想了解更多关于Python编程的知识，特别是关于{['变量', '函数', '类', '模块', '异常处理'][i % 5]}的内容。",
                    "tokens_used": 25,
                    "created_at": (datetime.now() - timedelta(minutes=50-i)).isoformat(),
                    "user_rating": 4 if i > 40 else 3,  # 最近的消息评分更高
                    "is_bookmarked": i in [5, 15, 25, 35]  # 一些重要消息被收藏
                })
            else:  # 助手消息
                messages.append({
                    "id": i,
                    "role": "ASSISTANT",
                    "content": f"关于{['变量', '函数', '类', '模块', '异常处理'][(i-1) % 5]}，我来为你详细解释。这是一个非常重要的概念，在Python编程中经常使用。让我通过示例来说明...",
                    "tokens_used": 35,
                    "created_at": (datetime.now() - timedelta(minutes=50-i)).isoformat(),
                    "confidence_score": 0.9,
                    "metadata": {"response_type": "educational"}
                })
        
        # 创建长对话上下文
        long_context = ConversationContextCache(
            conversation_id=long_conversation_id,
            messages=messages,
            token_count=sum(msg["tokens_used"] for msg in messages),
            summary=None,
            compression_applied=False
        )
        
        print(f"长对话上下文:")
        print(f"  对话ID: {long_conversation_id}")
        print(f"  消息数量: {len(long_context.messages)}")
        print(f"  Token数量: {long_context.token_count}")
        print(f"  是否已压缩: {long_context.compression_applied}")
        
        # 执行压缩
        print(f"\n执行智能压缩...")
        compressed_context = await self.context_cache._compress_context(long_context)
        
        print(f"压缩结果:")
        print(f"  压缩前消息数: {len(long_context.messages)}")
        print(f"  压缩后消息数: {len(compressed_context.messages)}")
        print(f"  压缩前Token数: {long_context.token_count}")
        print(f"  压缩后Token数: {compressed_context.token_count}")
        print(f"  压缩率: {(1 - len(compressed_context.messages) / len(long_context.messages)) * 100:.1f}%")
        print(f"  Token节省: {(1 - compressed_context.token_count / long_context.token_count) * 100:.1f}%")
        print(f"  生成摘要: {'✅ 是' if compressed_context.summary else '❌ 否'}")
        
        if compressed_context.summary:
            print(f"  摘要内容: {compressed_context.summary}")
        
        # 分析保留的消息类型
        preserved_messages = compressed_context.messages
        bookmarked_count = len([msg for msg in preserved_messages if msg.get('is_bookmarked')])
        high_rated_count = len([msg for msg in preserved_messages if msg.get('user_rating', 0) >= 4])
        
        print(f"\n保留消息分析:")
        print(f"  收藏消息数: {bookmarked_count}")
        print(f"  高评分消息数: {high_rated_count}")
        print(f"  最新消息占比: {len([msg for msg in preserved_messages if msg['id'] > 40]) / len(preserved_messages) * 100:.1f}%")
    
    async def demo_ai_context_generation(self):
        """演示AI上下文生成"""
        print("\n🤖 演示4: AI上下文生成")
        print("-" * 40)
        
        conversation_id = 1001
        user_id = 2001
        
        # 获取对话上下文
        existing_context = self.demo_conversations.get(conversation_id)
        if not existing_context:
            print("❌ 未找到对话上下文")
            return
        
        # 模拟获取上下文
        with patch.object(self.context_cache, 'get_conversation_context', return_value=existing_context):
            
            # 生成不同Token限制的上下文
            token_limits = [500, 1000, 2000]
            
            for max_tokens in token_limits:
                print(f"\n生成AI上下文 (最大{max_tokens} tokens):")
                
                context_str = await self.context_cache.get_context_for_ai(
                    conversation_id, user_id, max_tokens=max_tokens
                )
                
                print(f"  生成长度: {len(context_str)} 字符")
                print(f"  估算Token数: {len(context_str) // 4}")
                print(f"  包含消息数: {context_str.count('用户:') + context_str.count('助手:')}")
                
                # 显示上下文预览
                preview = context_str[:200] + "..." if len(context_str) > 200 else context_str
                print(f"  内容预览:")
                for line in preview.split('\n')[:3]:
                    if line.strip():
                        print(f"    {line}")
                
                # 验证格式
                has_user = "用户:" in context_str
                has_assistant = "助手:" in context_str
                print(f"  格式验证: {'✅ 正确' if has_user and has_assistant else '❌ 错误'}")
    
    async def demo_active_conversations(self):
        """演示活跃对话管理"""
        print("\n💬 演示5: 活跃对话管理")
        print("-" * 40)
        
        user_id = 2001
        
        # 模拟用户的活跃对话
        active_conversations = [1001, 1002, 1003, 1004, 1005]
        
        print(f"用户活跃对话:")
        print(f"  用户ID: {user_id}")
        print(f"  活跃对话数: {len(active_conversations)}")
        print(f"  对话ID列表: {active_conversations}")
        
        # 设置活跃对话
        with patch.object(self.context_cache.cache, 'set', return_value=True) as mock_set:
            success = await self.context_cache.set_user_active_conversations(
                user_id, active_conversations
            )
            
            print(f"  设置结果: {'✅ 成功' if success else '❌ 失败'}")
            
            if mock_set.called:
                call_args = mock_set.call_args
                print(f"  缓存键类型: {call_args[0][0].value}")
                print(f"  TTL设置: {call_args[1].get('ttl', '默认')}秒")
        
        # 获取活跃对话
        with patch.object(self.context_cache.cache, 'get', return_value=active_conversations):
            retrieved_conversations = await self.context_cache.get_user_active_conversations(user_id)
            
            print(f"\n检索活跃对话:")
            print(f"  检索到数量: {len(retrieved_conversations)}")
            print(f"  数据一致性: {'✅ 正确' if retrieved_conversations == active_conversations else '❌ 错误'}")
            
            # 模拟对话活跃度分析
            print(f"\n对话活跃度分析:")
            for conv_id in retrieved_conversations[:3]:  # 显示前3个
                last_activity = datetime.now() - timedelta(minutes=conv_id % 60)
                status = "活跃" if (datetime.now() - last_activity).seconds < 1800 else "不活跃"
                print(f"  对话{conv_id}: {status} (最后活动: {last_activity.strftime('%H:%M')})")
    
    async def demo_cache_monitoring(self):
        """演示缓存性能监控"""
        print("\n📊 演示6: 缓存性能监控")
        print("-" * 40)
        
        # 模拟缓存指标
        mock_metrics = {
            "hits": 150,
            "misses": 30,
            "sets": 80,
            "deletes": 10,
            "avg_access_time": 0.025
        }
        
        with patch.object(self.context_cache.cache, 'get_metrics', return_value=mock_metrics):
            stats = await self.context_cache.get_context_statistics()
            
            print(f"缓存性能统计:")
            
            if "context_cache_metrics" in stats:
                metrics = stats["context_cache_metrics"]
                total_ops = metrics.get("hits", 0) + metrics.get("misses", 0)
                hit_rate = metrics.get("hits", 0) / total_ops if total_ops > 0 else 0
                
                print(f"  命中次数: {metrics.get('hits', 0)}")
                print(f"  未命中次数: {metrics.get('misses', 0)}")
                print(f"  命中率: {hit_rate * 100:.1f}%")
                print(f"  设置次数: {metrics.get('sets', 0)}")
                print(f"  删除次数: {metrics.get('deletes', 0)}")
                print(f"  平均访问时间: {metrics.get('avg_access_time', 0) * 1000:.1f}ms")
            
            print(f"\n缓存配置:")
            print(f"  压缩阈值: {stats.get('compression_threshold', 0)} tokens")
            print(f"  最大上下文长度: {stats.get('max_context_length', 0)} tokens")
            
            if "cache_config" in stats:
                config = stats["cache_config"]
                print(f"  TTL设置: {config.ttl}秒")
                print(f"  最大大小: {config.max_size}")
                print(f"  压缩启用: {'✅ 是' if config.compression else '❌ 否'}")
                print(f"  缓存策略: {config.strategy.value}")
                print(f"  缓存级别: {config.level.value}")
        
        # 性能建议
        print(f"\n性能建议:")
        hit_rate = mock_metrics["hits"] / (mock_metrics["hits"] + mock_metrics["misses"])
        
        if hit_rate > 0.8:
            print("  ✅ 缓存命中率良好，系统性能优秀")
        elif hit_rate > 0.6:
            print("  ⚠️ 缓存命中率中等，可考虑优化缓存策略")
        else:
            print("  ❌ 缓存命中率较低，建议检查缓存配置")
        
        if mock_metrics["avg_access_time"] < 0.05:
            print("  ✅ 缓存访问速度快，用户体验良好")
        else:
            print("  ⚠️ 缓存访问速度较慢，可能需要优化")


async def main():
    """主演示函数"""
    demo = ContextCacheDemo()
    await demo.run_demo()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())