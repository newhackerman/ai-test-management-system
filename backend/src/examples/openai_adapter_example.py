"""
OpenAI适配器使用示例

演示如何使用OpenAI适配器进行各种AI操作。
"""

import asyncio
import os
import sys
import logging

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from adapters.base import (
    AIRequest, AdapterConfig, AIProvider, MessageRole, ChatMessage, ResponseFormat
)
from adapters.openai_adapter import OpenAIAdapter
from adapters.adapter_factory import AIAdapterFactory

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_chat_example():
    """基础聊天示例"""
    print("=== 基础聊天示例 ===")
    
    # 创建配置
    config = AdapterConfig(
        provider=AIProvider.OPENAI,
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
        default_model="gpt-3.5-turbo",
        timeout=30.0
    )
    
    # 创建适配器
    adapter = OpenAIAdapter(config)
    
    try:
        # 创建请求
        request = AIRequest(
            messages=[
                ChatMessage(role=MessageRole.SYSTEM, content="你是一个有用的AI助手。"),
                ChatMessage(role=MessageRole.USER, content="请介绍一下Python编程语言。")
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        # 发送请求
        response = await adapter.chat_completion(request)
        
        if response.success:
            print(f"响应: {response.content}")
            print(f"模型: {response.model}")
            print(f"Token使用: {response.usage.total_tokens if response.usage else 'N/A'}")
            print(f"响应时间: {response.response_time:.2f}秒")
        else:
            print(f"请求失败: {response.error_message}")
    
    finally:
        await adapter.shutdown()


async def streaming_chat_example():
    """流式聊天示例"""
    print("\n=== 流式聊天示例 ===")
    
    config = AdapterConfig(
        provider=AIProvider.OPENAI,
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
        default_model="gpt-3.5-turbo"
    )
    
    adapter = OpenAIAdapter(config)
    
    try:
        request = AIRequest(
            messages=[
                ChatMessage(role=MessageRole.USER, content="请写一首关于春天的短诗。")
            ],
            max_tokens=150,
            temperature=0.8
        )
        
        print("流式响应: ")
        async for chunk in adapter.stream_chat_completion(request):
            if not chunk.is_final:
                print(chunk.content, end="", flush=True)
            else:
                print(f"\n[完成 - 原因: {chunk.metadata.get('finish_reason', 'unknown')}]")
                break
    
    finally:
        await adapter.shutdown()


async def function_calling_example():
    """函数调用示例"""
    print("\n=== 函数调用示例 ===")
    
    config = AdapterConfig(
        provider=AIProvider.OPENAI,
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
        default_model="gpt-3.5-turbo"
    )
    
    adapter = OpenAIAdapter(config)
    
    try:
        # 定义函数
        functions = [
            {
                "name": "get_weather",
                "description": "获取指定城市的天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称，例如：北京、上海"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "温度单位"
                        }
                    },
                    "required": ["city"]
                }
            }
        ]
        
        request = AIRequest(
            messages=[
                ChatMessage(role=MessageRole.USER, content="北京今天天气怎么样？")
            ],
            functions=functions,
            function_call="auto",
            max_tokens=100
        )
        
        response = await adapter.chat_completion(request)
        
        if response.success:
            if response.function_call:
                print(f"AI想要调用函数: {response.function_call}")
            else:
                print(f"AI响应: {response.content}")
        else:
            print(f"请求失败: {response.error_message}")
    
    finally:
        await adapter.shutdown()


async def json_response_example():
    """JSON响应示例"""
    print("\n=== JSON响应示例 ===")
    
    config = AdapterConfig(
        provider=AIProvider.OPENAI,
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
        default_model="gpt-3.5-turbo"
    )
    
    adapter = OpenAIAdapter(config)
    
    try:
        request = AIRequest(
            messages=[
                ChatMessage(
                    role=MessageRole.SYSTEM, 
                    content="你是一个数据分析助手。请以JSON格式返回结果。"
                ),
                ChatMessage(
                    role=MessageRole.USER, 
                    content="分析以下数据并返回JSON格式的总结：销售额：[100, 200, 150, 300, 250]"
                )
            ],
            response_format=ResponseFormat.JSON,
            max_tokens=200
        )
        
        response = await adapter.chat_completion(request)
        
        if response.success:
            print(f"JSON响应: {response.content}")
            
            # 尝试解析JSON
            try:
                import json
                data = json.loads(response.content)
                print(f"解析成功: {data}")
            except json.JSONDecodeError:
                print("JSON解析失败")
        else:
            print(f"请求失败: {response.error_message}")
    
    finally:
        await adapter.shutdown()


async def multi_turn_conversation_example():
    """多轮对话示例"""
    print("\n=== 多轮对话示例 ===")
    
    config = AdapterConfig(
        provider=AIProvider.OPENAI,
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
        default_model="gpt-3.5-turbo"
    )
    
    adapter = OpenAIAdapter(config)
    
    try:
        # 初始化对话历史
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content="你是一个编程助手。")
        ]
        
        # 第一轮对话
        messages.append(ChatMessage(role=MessageRole.USER, content="什么是递归？"))
        
        request = AIRequest(messages=messages, max_tokens=150)
        response = await adapter.chat_completion(request)
        
        if response.success:
            print(f"用户: 什么是递归？")
            print(f"AI: {response.content}")
            
            # 添加AI响应到对话历史
            messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=response.content))
            
            # 第二轮对话
            messages.append(ChatMessage(role=MessageRole.USER, content="能给个Python递归的例子吗？"))
            
            request = AIRequest(messages=messages, max_tokens=200)
            response = await adapter.chat_completion(request)
            
            if response.success:
                print(f"\n用户: 能给个Python递归的例子吗？")
                print(f"AI: {response.content}")
            else:
                print(f"第二轮对话失败: {response.error_message}")
        else:
            print(f"第一轮对话失败: {response.error_message}")
    
    finally:
        await adapter.shutdown()


async def adapter_factory_example():
    """适配器工厂示例"""
    print("\n=== 适配器工厂示例 ===")
    
    # 使用工厂创建适配器
    config = AdapterConfig(
        provider=AIProvider.OPENAI,
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
        default_model="gpt-3.5-turbo"
    )
    
    adapter = AIAdapterFactory.create_adapter(config)
    
    try:
        # 健康检查
        is_healthy = await adapter.health_check()
        print(f"适配器健康状态: {is_healthy}")
        
        # 获取可用模型
        models = await adapter.get_available_models()
        print(f"可用模型数量: {len(models)}")
        print(f"部分模型: {models[:3]}")
        
        # 获取统计信息
        stats = adapter.get_stats()
        print(f"适配器统计: {stats}")
    
    finally:
        await adapter.shutdown()


async def error_handling_example():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")
    
    # 使用无效的API密钥
    config = AdapterConfig(
        provider=AIProvider.OPENAI,
        api_key="invalid-key",
        default_model="gpt-3.5-turbo",
        timeout=10.0
    )
    
    adapter = OpenAIAdapter(config)
    
    try:
        request = AIRequest(
            messages=[
                ChatMessage(role=MessageRole.USER, content="Hello!")
            ]
        )
        
        response = await adapter.chat_completion(request)
        
        if response.success:
            print(f"意外成功: {response.content}")
        else:
            print(f"预期的错误: {response.error_code} - {response.error_message}")
    
    finally:
        await adapter.shutdown()


async def main():
    """主函数"""
    print("OpenAI适配器使用示例")
    print("=" * 50)
    
    # 检查API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("警告: 请设置OPENAI_API_KEY环境变量或修改示例代码中的API密钥")
        print("某些示例可能会失败")
        print()
    
    try:
        # 运行所有示例
        await basic_chat_example()
        await streaming_chat_example()
        await function_calling_example()
        await json_response_example()
        await multi_turn_conversation_example()
        await adapter_factory_example()
        await error_handling_example()
        
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n示例运行出错: {str(e)}")
        logger.exception("示例运行异常")
    
    print("\n示例运行完成！")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())