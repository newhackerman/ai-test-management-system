"""
百度文心一言集成使用示例

本示例展示如何使用百度文心一言集成功能，包括：
1. 基础聊天对话
2. 流式响应处理
3. 模型推荐使用
4. 中文内容优化
5. 成本控制和监控

使用前请确保已配置正确的API密钥。
"""
import asyncio
import logging
import os
from typing import List

from ..services.baidu_wenxin_service import (
    BaiduWenxinService,
    initialize_wenxin_service,
    get_wenxin_service
)
from ..adapters.base import ChatMessage, MessageRole
from ..config.baidu_wenxin_config import (
    WenxinConfig,
    WenxinAPIConfig, 
    ChineseOptimizationConfig,
    WenxinEnvironment
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaiduWenxinExample:
    """百度文心一言使用示例"""
    
    def __init__(self):
        self.service = None
    
    async def initialize_service(self):
        """初始化服务"""
        # 从环境变量获取API密钥
        api_key = os.getenv("BAIDU_API_KEY")
        secret_key = os.getenv("BAIDU_SECRET_KEY")
        
        if not api_key or not secret_key:
            raise ValueError("请设置环境变量 BAIDU_API_KEY 和 BAIDU_SECRET_KEY")
        
        # 初始化服务
        self.service = await initialize_wenxin_service(
            api_key=api_key,
            secret_key=secret_key
        )
        
        logger.info("百度文心一言服务初始化完成")
    
    async def basic_chat_example(self):
        """基础聊天示例"""
        logger.info("=== 基础聊天示例 ===")
        
        # 创建对话消息
        messages = [
            ChatMessage(role=MessageRole.USER, content="你好，请介绍一下你自己")
        ]
        
        # 发送聊天请求
        response = await self.service.chat_completion(
            messages=messages,
            user_id=1,
            model="ernie-3.5-8k",
            temperature=0.7
        )
        
        if response.success:
            logger.info(f"AI回复: {response.content}")
            logger.info(f"使用模型: {response.model}")
            logger.info(f"响应时间: {response.response_time:.2f}秒")
            logger.info(f"Token使用: {response.usage.total_tokens if response.usage else 0}")
        else:
            logger.error(f"聊天失败: {response.error_message}")
    
    async def streaming_chat_example(self):
        """流式聊天示例"""
        logger.info("=== 流式聊天示例 ===")
        
        messages = [
            ChatMessage(role=MessageRole.USER, content="请写一首关于春天的诗")
        ]
        
        logger.info("AI正在创作中...")
        full_content = ""
        
        async for chunk in self.service.stream_chat_completion(
            messages=messages,
            user_id=1,
            model="ernie-4.0-8k"
        ):
            if chunk.content:
                print(chunk.content, end="", flush=True)
                full_content += chunk.content
            
            if chunk.is_final:
                break
        
        print("\n")
        logger.info(f"完整内容长度: {len(full_content)}字符")
    
    async def model_recommendation_example(self):
        """模型推荐示例"""
        logger.info("=== 模型推荐示例 ===")
        
        test_tasks = [
            "你好",
            "请解释一下机器学习的基本概念",
            "请设计一个完整的电商系统架构，包括前端、后端、数据库、缓存、消息队列等组件"
        ]
        
        for task in test_tasks:
            logger.info(f"\n任务: {task}")
            
            recommendations = await self.service.get_model_recommendations(task)
            
            logger.info("推荐模型:")
            for i, rec in enumerate(recommendations[:3], 1):  # 显示前3个推荐
                logger.info(f"  {i}. {rec.recommended_model.value}")
                logger.info(f"     置信度: {rec.confidence:.2f}")
                logger.info(f"     理由: {rec.reasoning}")
                logger.info(f"     预估成本: {rec.estimated_cost:.4f}元")
                logger.info(f"     预估时间: {rec.estimated_time:.1f}秒")
    
    async def chinese_optimization_example(self):
        """中文优化示例"""
        logger.info("=== 中文优化示例 ===")
        
        # 测试英文输入
        english_messages = [
            ChatMessage(role=MessageRole.USER, content="Hello, can you help me with programming?")
        ]
        
        response = await self.service.chat_completion(
            messages=english_messages,
            user_id=1,
            model="ernie-3.5-8k"
        )
        
        if response.success:
            logger.info("英文输入，中文回复:")
            logger.info(f"输入: Hello, can you help me with programming?")
            logger.info(f"输出: {response.content[:200]}...")
            
            # 分析中文比例
            chinese_chars = sum(1 for char in response.content if '\u4e00' <= char <= '\u9fff')
            total_chars = len(response.content)
            chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
            
            logger.info(f"中文字符比例: {chinese_ratio:.1%}")
    
    async def multi_turn_conversation_example(self):
        """多轮对话示例"""
        logger.info("=== 多轮对话示例 ===")
        
        conversation_history = []
        
        # 第一轮
        user_message1 = "我想学习Python编程，应该从哪里开始？"
        conversation_history.append(ChatMessage(role=MessageRole.USER, content=user_message1))
        
        response1 = await self.service.chat_completion(
            messages=conversation_history,
            user_id=1,
            conversation_id="conv_001"
        )
        
        if response1.success:
            logger.info(f"用户: {user_message1}")
            logger.info(f"AI: {response1.content[:150]}...")
            conversation_history.append(ChatMessage(role=MessageRole.ASSISTANT, content=response1.content))
        
        # 第二轮
        user_message2 = "那具体应该学习哪些基础知识呢？"
        conversation_history.append(ChatMessage(role=MessageRole.USER, content=user_message2))
        
        response2 = await self.service.chat_completion(
            messages=conversation_history,
            user_id=1,
            conversation_id="conv_001"
        )
        
        if response2.success:
            logger.info(f"用户: {user_message2}")
            logger.info(f"AI: {response2.content[:150]}...")
            conversation_history.append(ChatMessage(role=MessageRole.ASSISTANT, content=response2.content))
        
        logger.info(f"对话轮数: {len([msg for msg in conversation_history if msg.role == MessageRole.USER])}")
    
    async def cost_monitoring_example(self):
        """成本监控示例"""
        logger.info("=== 成本监控示例 ===")
        
        # 获取使用统计
        stats = await self.service.get_usage_statistics()
        
        logger.info("使用统计:")
        logger.info(f"  总请求数: {stats['total_requests']}")
        logger.info(f"  成功请求数: {stats['successful_requests']}")
        logger.info(f"  成功率: {stats['success_rate']:.1%}")
        logger.info(f"  总Token数: {stats['total_tokens']}")
        logger.info(f"  总成本: {stats['total_cost']:.4f}元")
        logger.info(f"  平均响应时间: {stats['avg_response_time']:.2f}秒")
        logger.info(f"  单次请求平均成本: {stats['cost_per_request']:.4f}元")
        
        if stats['model_usage']:
            logger.info("模型使用分布:")
            for model, count in stats['model_usage'].items():
                percentage = count / stats['total_requests'] * 100 if stats['total_requests'] > 0 else 0
                logger.info(f"  {model}: {count}次 ({percentage:.1f}%)")
    
    async def error_handling_example(self):
        """错误处理示例"""
        logger.info("=== 错误处理示例 ===")
        
        try:
            # 故意使用无效参数
            messages = [ChatMessage(role=MessageRole.USER, content="测试")]
            
            response = await self.service.chat_completion(
                messages=messages,
                user_id=1,
                model="invalid-model",  # 无效模型
                max_tokens=-1  # 无效参数
            )
            
            if not response.success:
                logger.info(f"预期的错误: {response.error_message}")
            
        except Exception as e:
            logger.info(f"捕获异常: {type(e).__name__}: {e}")
    
    async def performance_comparison_example(self):
        """性能对比示例"""
        logger.info("=== 性能对比示例 ===")
        
        models = ["ernie-speed-8k", "ernie-turbo-8k", "ernie-3.5-8k", "ernie-4.0-8k"]
        test_message = "请简单介绍一下人工智能的发展历程"
        
        results = {}
        
        for model in models:
            try:
                messages = [ChatMessage(role=MessageRole.USER, content=test_message)]
                
                import time
                start_time = time.time()
                
                response = await self.service.chat_completion(
                    messages=messages,
                    user_id=1,
                    model=model
                )
                
                end_time = time.time()
                
                if response.success:
                    results[model] = {
                        "response_time": end_time - start_time,
                        "content_length": len(response.content),
                        "tokens_used": response.usage.total_tokens if response.usage else 0,
                        "confidence": response.confidence_score or 0
                    }
                    
                    logger.info(f"{model}:")
                    logger.info(f"  响应时间: {results[model]['response_time']:.2f}秒")
                    logger.info(f"  内容长度: {results[model]['content_length']}字符")
                    logger.info(f"  Token使用: {results[model]['tokens_used']}")
                    logger.info(f"  质量评分: {results[model]['confidence']:.2f}")
                
                # 避免请求过于频繁
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"{model} 测试失败: {e}")
        
        # 性能总结
        if results:
            fastest_model = min(results.keys(), key=lambda k: results[k]['response_time'])
            highest_quality = max(results.keys(), key=lambda k: results[k]['confidence'])
            
            logger.info(f"\n性能总结:")
            logger.info(f"  最快模型: {fastest_model} ({results[fastest_model]['response_time']:.2f}秒)")
            logger.info(f"  最高质量: {highest_quality} (评分: {results[highest_quality]['confidence']:.2f})")
    
    async def run_all_examples(self):
        """运行所有示例"""
        logger.info("🚀 开始运行百度文心一言使用示例")
        logger.info("=" * 50)
        
        try:
            # 初始化服务
            await self.initialize_service()
            
            # 运行各种示例
            await self.basic_chat_example()
            await asyncio.sleep(1)
            
            await self.streaming_chat_example()
            await asyncio.sleep(1)
            
            await self.model_recommendation_example()
            await asyncio.sleep(1)
            
            await self.chinese_optimization_example()
            await asyncio.sleep(1)
            
            await self.multi_turn_conversation_example()
            await asyncio.sleep(1)
            
            await self.cost_monitoring_example()
            await asyncio.sleep(1)
            
            await self.error_handling_example()
            await asyncio.sleep(1)
            
            await self.performance_comparison_example()
            
            logger.info("\n🎉 所有示例运行完成！")
            
        except Exception as e:
            logger.error(f"示例运行失败: {e}")
            raise


async def main():
    """主函数"""
    # 检查环境变量
    if not os.getenv("BAIDU_API_KEY") or not os.getenv("BAIDU_SECRET_KEY"):
        print("请设置环境变量:")
        print("export BAIDU_API_KEY=your_api_key")
        print("export BAIDU_SECRET_KEY=your_secret_key")
        return
    
    # 运行示例
    example = BaiduWenxinExample()
    await example.run_all_examples()


if __name__ == "__main__":
    asyncio.run(main())