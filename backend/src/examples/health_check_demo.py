#!/usr/bin/env python3
"""
AI适配器健康检查机制演示

这个脚本演示了如何使用健康检查服务来监控AI适配器的健康状态。

功能包括：
1. 基础健康检查
2. 功能性健康检查
3. 性能健康检查
4. 综合健康检查
5. 实时监控和告警
6. 健康状态报告

使用方法:
    python health_check_demo.py
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# 添加路径以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from adapters.base import BaseAIAdapter, AIRequest, AIResponse, AdapterConfig, AIProvider, MessageRole, ChatMessage
from adapters.openai_adapter import OpenAIAdapter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthCheckDemo:
    """健康检查演示类"""
    
    def __init__(self):
        self.adapters = {}
        self.health_results = {}
        self.monitoring_active = False
    
    def create_demo_adapters(self):
        """创建演示用的适配器"""
        print("🔧 创建演示适配器...")
        
        # 注意：这里使用模拟的API密钥，实际使用时需要真实的API密钥
        configs = [
            {
                "name": "openai-gpt35",
                "config": AdapterConfig(
                    provider=AIProvider.OPENAI,
                    api_key="demo-key-openai",  # 演示用密钥
                    default_model="gpt-3.5-turbo",
                    timeout=10.0
                ),
                "description": "OpenAI GPT-3.5 适配器"
            },
            {
                "name": "openai-gpt4",
                "config": AdapterConfig(
                    provider=AIProvider.OPENAI,
                    api_key="demo-key-openai-gpt4",  # 演示用密钥
                    default_model="gpt-4",
                    timeout=15.0
                ),
                "description": "OpenAI GPT-4 适配器"
            }
        ]
        
        for adapter_info in configs:
            try:
                # 在实际环境中，这里会创建真实的适配器
                # 为了演示，我们创建模拟适配器
                adapter = self.create_mock_adapter(adapter_info["config"])
                self.adapters[adapter_info["name"]] = {
                    "adapter": adapter,
                    "config": adapter_info["config"],
                    "description": adapter_info["description"]
                }
                print(f"  ✅ {adapter_info['name']}: {adapter_info['description']}")
            except Exception as e:
                print(f"  ❌ {adapter_info['name']}: 创建失败 - {str(e)}")
        
        print(f"📊 总共创建了 {len(self.adapters)} 个适配器\n")
    
    def create_mock_adapter(self, config: AdapterConfig):
        """创建模拟适配器（用于演示）"""
        
        class MockAdapter(BaseAIAdapter):
            def __init__(self, config):
                super().__init__(config)
                self.demo_healthy = True
                self.demo_response_time = 0.1
            
            async def chat_completion(self, request: AIRequest) -> AIResponse:
                await asyncio.sleep(self.demo_response_time)
                
                if self.demo_healthy:
                    return AIResponse(
                        request_id=request.request_id,
                        provider=self.provider,
                        model=config.default_model or "demo-model",
                        content=f"演示响应: {request.messages[-1].content}",
                        response_time=self.demo_response_time,
                        success=True
                    )
                else:
                    return AIResponse.create_error_response(
                        request.request_id, self.provider,
                        "DEMO_ERROR", "演示错误"
                    )
            
            async def stream_chat_completion(self, request: AIRequest):
                yield {"content": "演示流式响应", "is_final": True}
            
            async def get_available_models(self):
                return [config.default_model or "demo-model"]
            
            async def health_check(self) -> bool:
                await asyncio.sleep(0.05)  # 模拟检查时间
                return self.demo_healthy
        
        return MockAdapter(config)
    
    async def demonstrate_basic_health_check(self):
        """演示基础健康检查"""
        print("🏥 基础健康检查演示")
        print("=" * 50)
        
        for name, adapter_info in self.adapters.items():
            adapter = adapter_info["adapter"]
            description = adapter_info["description"]
            
            print(f"\n检查适配器: {name}")
            print(f"描述: {description}")
            
            try:
                start_time = datetime.now(timezone.utc)
                is_healthy = await adapter.health_check()
                end_time = datetime.now(timezone.utc)
                
                response_time = (end_time - start_time).total_seconds()
                
                status = "✅ 健康" if is_healthy else "❌ 不健康"
                print(f"状态: {status}")
                print(f"响应时间: {response_time:.3f}s")
                
                # 记录结果
                self.health_results[name] = {
                    "healthy": is_healthy,
                    "response_time": response_time,
                    "timestamp": end_time,
                    "check_type": "basic"
                }
                
            except Exception as e:
                print(f"状态: ❌ 检查失败")
                print(f"错误: {str(e)}")
                
                self.health_results[name] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc),
                    "check_type": "basic"
                }
        
        print("\n" + "=" * 50)
    
    async def demonstrate_functional_health_check(self):
        """演示功能性健康检查"""
        print("\n🔧 功能性健康检查演示")
        print("=" * 50)
        
        test_request = AIRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="这是一个健康检查测试消息")]
        )
        
        for name, adapter_info in self.adapters.items():
            adapter = adapter_info["adapter"]
            
            print(f"\n测试适配器: {name}")
            
            try:
                start_time = datetime.now(timezone.utc)
                response = await adapter.chat_completion(test_request)
                end_time = datetime.now(timezone.utc)
                
                response_time = (end_time - start_time).total_seconds()
                
                if response.success:
                    print(f"状态: ✅ 功能正常")
                    print(f"响应时间: {response_time:.3f}s")
                    print(f"响应内容: {response.content[:50]}...")
                else:
                    print(f"状态: ❌ 功能异常")
                    print(f"错误: {response.error_message}")
                
                # 更新结果
                if name in self.health_results:
                    self.health_results[name].update({
                        "functional_test": response.success,
                        "functional_response_time": response_time,
                        "functional_content": response.content if response.success else None
                    })
                
            except Exception as e:
                print(f"状态: ❌ 测试失败")
                print(f"错误: {str(e)}")
        
        print("\n" + "=" * 50)
    
    async def demonstrate_performance_monitoring(self):
        """演示性能监控"""
        print("\n📊 性能监控演示")
        print("=" * 50)
        
        # 并发测试
        concurrent_requests = 3
        
        for name, adapter_info in self.adapters.items():
            adapter = adapter_info["adapter"]
            
            print(f"\n性能测试: {name}")
            print(f"并发请求数: {concurrent_requests}")
            
            try:
                # 创建并发请求
                test_requests = [
                    AIRequest(
                        messages=[ChatMessage(role=MessageRole.USER, content=f"性能测试请求 #{i+1}")]
                    )
                    for i in range(concurrent_requests)
                ]
                
                start_time = datetime.now(timezone.utc)
                
                # 并发执行
                tasks = [adapter.chat_completion(req) for req in test_requests]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = datetime.now(timezone.utc)
                total_time = (end_time - start_time).total_seconds()
                
                # 分析结果
                successful_responses = [
                    r for r in responses 
                    if isinstance(r, AIResponse) and r.success
                ]
                
                success_rate = len(successful_responses) / len(responses)
                avg_response_time = (
                    sum(r.response_time for r in successful_responses) / len(successful_responses)
                    if successful_responses else 0
                )
                throughput = len(successful_responses) / total_time if total_time > 0 else 0
                
                print(f"总耗时: {total_time:.3f}s")
                print(f"成功率: {success_rate:.1%}")
                print(f"平均响应时间: {avg_response_time:.3f}s")
                print(f"吞吐量: {throughput:.1f} 请求/秒")
                
                # 性能评估
                if success_rate >= 0.9 and avg_response_time < 2.0:
                    performance_status = "✅ 性能良好"
                elif success_rate >= 0.7 and avg_response_time < 5.0:
                    performance_status = "⚠️ 性能一般"
                else:
                    performance_status = "❌ 性能不佳"
                
                print(f"性能评估: {performance_status}")
                
                # 更新结果
                if name in self.health_results:
                    self.health_results[name].update({
                        "performance_success_rate": success_rate,
                        "performance_avg_response_time": avg_response_time,
                        "performance_throughput": throughput,
                        "performance_status": performance_status
                    })
                
            except Exception as e:
                print(f"性能测试失败: {str(e)}")
        
        print("\n" + "=" * 50)
    
    def generate_health_report(self):
        """生成健康状态报告"""
        print("\n📋 健康状态报告")
        print("=" * 50)
        
        if not self.health_results:
            print("❌ 没有健康检查数据")
            return
        
        # 统计信息
        total_adapters = len(self.health_results)
        healthy_adapters = sum(1 for result in self.health_results.values() if result.get("healthy", False))
        unhealthy_adapters = total_adapters - healthy_adapters
        
        print(f"📊 总体统计:")
        print(f"  总适配器数: {total_adapters}")
        print(f"  健康适配器: {healthy_adapters} ({healthy_adapters/total_adapters:.1%})")
        print(f"  不健康适配器: {unhealthy_adapters} ({unhealthy_adapters/total_adapters:.1%})")
        
        # 详细报告
        print(f"\n📝 详细报告:")
        for name, result in self.health_results.items():
            print(f"\n🔸 {name}:")
            
            # 基础健康状态
            health_status = "✅ 健康" if result.get("healthy", False) else "❌ 不健康"
            print(f"  基础状态: {health_status}")
            
            if "response_time" in result:
                print(f"  响应时间: {result['response_time']:.3f}s")
            
            # 功能测试结果
            if "functional_test" in result:
                func_status = "✅ 正常" if result["functional_test"] else "❌ 异常"
                print(f"  功能测试: {func_status}")
                
                if "functional_response_time" in result:
                    print(f"  功能响应时间: {result['functional_response_time']:.3f}s")
            
            # 性能测试结果
            if "performance_success_rate" in result:
                print(f"  性能成功率: {result['performance_success_rate']:.1%}")
                print(f"  平均响应时间: {result['performance_avg_response_time']:.3f}s")
                print(f"  吞吐量: {result['performance_throughput']:.1f} 请求/秒")
                print(f"  性能评估: {result['performance_status']}")
            
            # 错误信息
            if "error" in result:
                print(f"  错误信息: {result['error']}")
            
            print(f"  检查时间: {result['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        print("\n" + "=" * 50)
    
    async def demonstrate_real_time_monitoring(self):
        """演示实时监控"""
        print("\n⏰ 实时监控演示 (10秒)")
        print("=" * 50)
        
        self.monitoring_active = True
        monitor_duration = 10  # 监控10秒
        check_interval = 2     # 每2秒检查一次
        
        print(f"开始实时监控，持续 {monitor_duration} 秒，每 {check_interval} 秒检查一次...")
        
        start_time = datetime.now()
        check_count = 0
        
        while self.monitoring_active and (datetime.now() - start_time).total_seconds() < monitor_duration:
            check_count += 1
            current_time = datetime.now().strftime('%H:%M:%S')
            
            print(f"\n🔍 第 {check_count} 次检查 ({current_time}):")
            
            for name, adapter_info in self.adapters.items():
                adapter = adapter_info["adapter"]
                
                try:
                    is_healthy = await adapter.health_check()
                    status = "✅" if is_healthy else "❌"
                    print(f"  {name}: {status}")
                    
                    # 模拟状态变化（演示用）
                    if check_count == 3 and name == "openai-gpt35":
                        adapter.demo_healthy = False
                        print(f"    📢 模拟 {name} 状态变为不健康")
                    elif check_count == 5 and name == "openai-gpt35":
                        adapter.demo_healthy = True
                        print(f"    📢 模拟 {name} 状态恢复健康")
                    
                except Exception as e:
                    print(f"  {name}: ❌ (错误: {str(e)})")
            
            await asyncio.sleep(check_interval)
        
        print(f"\n⏹️ 实时监控结束，共执行了 {check_count} 次检查")
        print("=" * 50)
    
    async def run_demo(self):
        """运行完整演示"""
        print("🚀 AI适配器健康检查机制演示")
        print("=" * 60)
        print("这个演示将展示以下功能:")
        print("1. 基础健康检查")
        print("2. 功能性健康检查")
        print("3. 性能监控")
        print("4. 健康状态报告")
        print("5. 实时监控")
        print("=" * 60)
        
        # 创建适配器
        self.create_demo_adapters()
        
        # 等待用户确认
        input("按 Enter 键开始演示...")
        
        try:
            # 1. 基础健康检查
            await self.demonstrate_basic_health_check()
            
            # 2. 功能性健康检查
            await self.demonstrate_functional_health_check()
            
            # 3. 性能监控
            await self.demonstrate_performance_monitoring()
            
            # 4. 生成报告
            self.generate_health_report()
            
            # 5. 实时监控
            print("\n是否要演示实时监控? (y/n): ", end="")
            if input().lower().startswith('y'):
                await self.demonstrate_real_time_monitoring()
            
        except KeyboardInterrupt:
            print("\n\n⏹️ 演示被用户中断")
            self.monitoring_active = False
        
        print("\n🎉 演示完成！")
        print("\n💡 总结:")
        print("- 健康检查机制可以有效监控AI适配器状态")
        print("- 支持多种检查类型：基础、功能性、性能")
        print("- 提供实时监控和状态变化通知")
        print("- 生成详细的健康状态报告")
        print("- 可以集成到生产环境中进行持续监控")


async def main():
    """主函数"""
    demo = HealthCheckDemo()
    await demo.run_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()