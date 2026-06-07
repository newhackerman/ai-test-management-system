"""
AI服务提供商适配器模块

本模块实现了多AI服务提供商的统一适配器架构，提供：
1. 统一的AI服务调用接口
2. 多种AI服务提供商的适配器实现
3. 智能路由和负载均衡
4. 错误处理和故障转移
5. 性能监控和成本控制

支持的AI服务提供商：
- OpenAI (GPT-4, GPT-3.5-turbo)
- Anthropic (Claude-3 系列)
- 百度文心一言
- 阿里通义千问
- Google Gemini
- 智谱ChatGLM
- 科大讯飞星火
- 自定义AI服务

架构特点：
- 插件化设计，易于扩展新的AI服务提供商
- 统一的请求/响应格式
- 异步编程模式，支持高并发
- 智能重试和故障恢复
- 详细的性能监控和日志记录
"""

from .base import BaseAIAdapter, AIRequest, AIResponse, AIProvider
from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .baidu_adapter import BaiduAdapter
from .aliyun_adapter import AliyunAdapter
from .google_adapter import GoogleAdapter
from .zhipu_adapter import ZhipuAdapter
from .xunfei_adapter import XunfeiAdapter
from .custom_adapter import CustomAdapter
from .adapter_manager import AdapterManager

__all__ = [
    # 基础类
    'BaseAIAdapter',
    'AIRequest', 
    'AIResponse',
    'AIProvider',
    
    # 具体适配器
    'OpenAIAdapter',
    'AnthropicAdapter', 
    'BaiduAdapter',
    'AliyunAdapter',
    'GoogleAdapter',
    'ZhipuAdapter',
    'XunfeiAdapter',
    'CustomAdapter',
    
    # 管理器
    'AdapterManager'
]