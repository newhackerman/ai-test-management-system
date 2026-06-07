"""
百度文心一言集成初始化脚本

本脚本用于初始化和测试百度文心一言集成功能，包括：
1. 服务初始化和配置
2. 连接测试和验证
3. 模型功能测试
4. 性能基准测试
5. 配置优化建议

使用方法：
python -m backend.src.scripts.init_baidu_wenxin --api-key YOUR_API_KEY --secret-key YOUR_SECRET_KEY
"""
import asyncio
import argparse
import logging
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.src.services.baidu_wenxin_service import (
    BaiduWenxinService, 
    WenxinModel, 
    TaskComplexity,
    initialize_wenxin_service,
    get_wenxin_service
)
from backend.src.adapters.base import ChatMessage, MessageRole
from backend.src.config.baidu_wenxin_config import (
    WenxinConfig, 
    WenxinAPIConfig, 
    ChineseOptimizationConfig,
    WenxinEnvironment,
    get_model_config,
    validate_wenxin_config
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaiduWenxinInitializer:
    """百度文心一言初始化器"""
    
    def __init__(self, api_key: str, secret_key: str, environment: str = "production"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.environment = WenxinEnvironment(environment)
        self.service = None
        
        # 测试配置
        self.test_messages = [
            "你好，请介绍一下你自己。",
            "请解释一下人工智能的基本概念。",
            "请分析一下当前AI技术的发展趋势和挑战。",
            "请写一首关于春天的诗。",
            "请帮我设计一个简单的Web应用架构。"
        ]
    
    async def initialize(self):
        """初始化百度文心一言服务"""
        try:
            logger.info("开始初始化百度文心一言服务...")
            
            # 创建配置
            config = WenxinConfig(
                api_config=WenxinAPIConfig(
                    api_key=self.api_key,
                    secret_key=self.secret_key,
                    environment=self.environment,
                    timeout=30.0,
                    max_retries=3,
                    max_concurrent_requests=10
                ),
                chinese_optimization=ChineseOptimizationConfig(
                    enable_context_enhancement=True,
                    use_chinese_punctuation=True,
                    optimize_for_chinese_culture=True,
                    enable_idiom_usage=True
                ),
                enable_streaming=True,
                enable_response_caching=True
            )
            
            # 验证配置
            errors = validate_wenxin_config(config)
            if errors:
                logger.error("配置验证失败:")
                for error in errors:
                    logger.error(f"  - {error}")
                return False
            
            # 初始化服务
            self.service = await initialize_wenxin_service(
                api_key=self.api_key,
                secret_key=self.secret_key
            )
            
            logger.info("百度文心一言服务初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    async def test_connection(self):
        """测试连接"""
        logger.info("测试百度文心一言连接...")
        
        try:
            # 健康检查
            health_info = await self.service.health_check()
            
            if health_info["healthy"]:
                logger.info("✅ 连接测试成功")
                logger.info(f"可用模型数量: {len(health_info['available_models'])}")
                
                # 显示可用模型
                logger.info("可用模型列表:")
                for model in health_info['available_models']:
                    model_info = get_model_config(model)
                    if model_info:
                        logger.info(f"  - {model_info.display_name} ({model})")
                        logger.info(f"    成本: {model_info.cost_per_1k_tokens}元/1K tokens")
                        logger.info(f"    响应时间: ~{model_info.avg_response_time}秒")
                
                return True
            else:
                logger.error("❌ 连接测试失败")
                logger.error(f"错误信息: {health_info.get('error', 'Unknown')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 连接测试异常: {e}")
            return False
    
    async def test_basic_chat(self):
        """测试基础聊天功能"""
        logger.info("测试基础聊天功能...")
        
        try:
            messages = [ChatMessage(role=MessageRole.USER, content="你好")]
            
            response = await self.service.chat_completion(
                messages=messages,
                user_id=1,
                model="ernie-speed-8k"  # 使用最快的模型进行测试
            )
            
            if response.success:
                logger.info("✅ 基础聊天测试成功")
                logger.info(f"响应内容: {response.content[:100]}...")
                logger.info(f"响应时间: {response.response_time:.2f}秒")
                logger.info(f"Token使用: {response.usage.total_tokens if response.usage else 0}")
                return True
            else:
                logger.error("❌ 基础聊天测试失败")
                logger.error(f"错误信息: {response.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 基础聊天测试异常: {e}")
            return False
    
    async def test_streaming_chat(self):
        """测试流式聊天功能"""
        logger.info("测试流式聊天功能...")
        
        try:
            messages = [ChatMessage(role=MessageRole.USER, content="请简单介绍一下人工智能")]
            
            chunks = []
            start_time = time.time()
            
            async for chunk in self.service.stream_chat_completion(
                messages=messages,
                user_id=1,
                model="ernie-speed-8k"
            ):
                chunks.append(chunk)
                if chunk.is_final:
                    break
            
            end_time = time.time()
            
            if chunks:
                logger.info("✅ 流式聊天测试成功")
                logger.info(f"接收到 {len(chunks)} 个数据块")
                logger.info(f"总耗时: {end_time - start_time:.2f}秒")
                
                # 拼接完整内容
                full_content = "".join(chunk.content for chunk in chunks if chunk.content)
                logger.info(f"完整响应: {full_content[:100]}...")
                return True
            else:
                logger.error("❌ 流式聊天测试失败: 未接收到数据")
                return False
                
        except Exception as e:
            logger.error(f"❌ 流式聊天测试异常: {e}")
            return False
    
    async def test_model_recommendation(self):
        """测试模型推荐功能"""
        logger.info("测试模型推荐功能...")
        
        try:
            test_cases = [
                ("你好", TaskComplexity.SIMPLE),
                ("请解释一下机器学习的基本概念", TaskComplexity.MEDIUM),
                ("请设计一个完整的微服务架构方案", TaskComplexity.COMPLEX)
            ]
            
            success_count = 0
            
            for task_description, expected_complexity in test_cases:
                recommendations = await self.service.get_model_recommendations(task_description)
                
                if recommendations:
                    best_recommendation = recommendations[0]
                    logger.info(f"任务: {task_description[:30]}...")
                    logger.info(f"推荐模型: {best_recommendation.recommended_model.value}")
                    logger.info(f"置信度: {best_recommendation.confidence:.2f}")
                    logger.info(f"推荐理由: {best_recommendation.reasoning}")
                    success_count += 1
                else:
                    logger.warning(f"任务推荐失败: {task_description}")
            
            if success_count == len(test_cases):
                logger.info("✅ 模型推荐测试成功")
                return True
            else:
                logger.warning(f"⚠️ 模型推荐部分成功: {success_count}/{len(test_cases)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 模型推荐测试异常: {e}")
            return False
    
    async def test_chinese_optimization(self):
        """测试中文优化功能"""
        logger.info("测试中文优化功能...")
        
        try:
            # 测试英文输入的中文优化
            messages = [ChatMessage(role=MessageRole.USER, content="Hello, how are you?")]
            
            response = await self.service.chat_completion(
                messages=messages,
                user_id=1,
                model="ernie-speed-8k"
            )
            
            if response.success:
                # 检查响应是否为中文
                chinese_chars = sum(1 for char in response.content if '\u4e00' <= char <= '\u9fff')
                total_chars = len(response.content)
                chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
                
                logger.info("✅ 中文优化测试成功")
                logger.info(f"响应内容: {response.content[:100]}...")
                logger.info(f"中文字符比例: {chinese_ratio:.2%}")
                
                # 检查中文标点
                has_chinese_punctuation = any(punct in response.content for punct in ['，', '。', '？', '！'])
                logger.info(f"包含中文标点: {'是' if has_chinese_punctuation else '否'}")
                
                return True
            else:
                logger.error("❌ 中文优化测试失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 中文优化测试异常: {e}")
            return False
    
    async def performance_benchmark(self):
        """性能基准测试"""
        logger.info("开始性能基准测试...")
        
        try:
            models_to_test = ["ernie-speed-8k", "ernie-turbo-8k", "ernie-3.5-8k"]
            results = {}
            
            for model in models_to_test:
                logger.info(f"测试模型: {model}")
                
                # 测试多个请求
                response_times = []
                success_count = 0
                
                for i, test_message in enumerate(self.test_messages):
                    try:
                        messages = [ChatMessage(role=MessageRole.USER, content=test_message)]
                        
                        start_time = time.time()
                        response = await self.service.chat_completion(
                            messages=messages,
                            user_id=1,
                            model=model
                        )
                        end_time = time.time()
                        
                        if response.success:
                            response_times.append(end_time - start_time)
                            success_count += 1
                            logger.info(f"  请求 {i+1}: {end_time - start_time:.2f}秒")
                        else:
                            logger.warning(f"  请求 {i+1}: 失败")
                        
                        # 避免请求过于频繁
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.warning(f"  请求 {i+1}: 异常 - {e}")
                
                # 计算统计数据
                if response_times:
                    avg_time = sum(response_times) / len(response_times)
                    min_time = min(response_times)
                    max_time = max(response_times)
                    
                    results[model] = {
                        "success_rate": success_count / len(self.test_messages),
                        "avg_response_time": avg_time,
                        "min_response_time": min_time,
                        "max_response_time": max_time,
                        "total_requests": len(self.test_messages)
                    }
                    
                    logger.info(f"  成功率: {success_count}/{len(self.test_messages)} ({success_count/len(self.test_messages):.1%})")
                    logger.info(f"  平均响应时间: {avg_time:.2f}秒")
                    logger.info(f"  响应时间范围: {min_time:.2f}s - {max_time:.2f}s")
                else:
                    results[model] = {
                        "success_rate": 0,
                        "error": "所有请求都失败"
                    }
            
            # 显示性能对比
            logger.info("\n性能基准测试结果:")
            logger.info("-" * 60)
            logger.info(f"{'模型':<20} {'成功率':<10} {'平均响应时间':<15} {'响应范围':<20}")
            logger.info("-" * 60)
            
            for model, result in results.items():
                if "error" not in result:
                    logger.info(
                        f"{model:<20} "
                        f"{result['success_rate']:.1%}    "
                        f"{result['avg_response_time']:.2f}秒         "
                        f"{result['min_response_time']:.2f}s-{result['max_response_time']:.2f}s"
                    )
                else:
                    logger.info(f"{model:<20} 失败      {result['error']}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 性能基准测试异常: {e}")
            return {}
    
    async def test_cost_calculation(self):
        """测试成本计算"""
        logger.info("测试成本计算功能...")
        
        try:
            # 获取使用统计
            stats = await self.service.get_usage_statistics()
            
            logger.info("✅ 成本计算测试成功")
            logger.info(f"总请求数: {stats['total_requests']}")
            logger.info(f"成功请求数: {stats['successful_requests']}")
            logger.info(f"总Token数: {stats['total_tokens']}")
            logger.info(f"总成本: {stats['total_cost']:.4f}元")
            logger.info(f"平均每请求成本: {stats['cost_per_request']:.4f}元")
            
            # 显示模型使用分布
            if stats['model_usage']:
                logger.info("模型使用分布:")
                for model, count in stats['model_usage'].items():
                    percentage = count / stats['total_requests'] * 100 if stats['total_requests'] > 0 else 0
                    logger.info(f"  {model}: {count}次 ({percentage:.1f}%)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 成本计算测试异常: {e}")
            return False
    
    async def generate_optimization_report(self):
        """生成优化建议报告"""
        logger.info("生成优化建议报告...")
        
        try:
            stats = await self.service.get_usage_statistics()
            
            recommendations = []
            
            # 基于成功率的建议
            if stats['success_rate'] < 0.9:
                recommendations.append({
                    "type": "reliability",
                    "priority": "high",
                    "issue": f"成功率较低 ({stats['success_rate']:.1%})",
                    "suggestion": "检查网络连接和API配置，考虑增加重试机制"
                })
            
            # 基于响应时间的建议
            if stats['avg_response_time'] > 5.0:
                recommendations.append({
                    "type": "performance",
                    "priority": "medium",
                    "issue": f"平均响应时间较长 ({stats['avg_response_time']:.2f}秒)",
                    "suggestion": "考虑使用更快的模型或优化请求参数"
                })
            
            # 基于成本的建议
            if stats['cost_per_request'] > 0.1:
                recommendations.append({
                    "type": "cost",
                    "priority": "medium",
                    "issue": f"单次请求成本较高 ({stats['cost_per_request']:.4f}元)",
                    "suggestion": "考虑使用成本更低的模型或优化Token使用"
                })
            
            # 基于模型使用的建议
            if stats['model_usage']:
                total_requests = sum(stats['model_usage'].values())
                expensive_model_ratio = stats['model_usage'].get('ernie-4.0-8k', 0) / total_requests
                
                if expensive_model_ratio > 0.5:
                    recommendations.append({
                        "type": "cost_optimization",
                        "priority": "low",
                        "issue": f"高成本模型使用比例较高 ({expensive_model_ratio:.1%})",
                        "suggestion": "评估是否可以在部分场景使用成本更低的模型"
                    })
            
            # 输出报告
            if recommendations:
                logger.info("\n📊 优化建议报告:")
                logger.info("=" * 50)
                
                for i, rec in enumerate(recommendations, 1):
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                    logger.info(f"{i}. {priority_emoji.get(rec['priority'], '⚪')} [{rec['type'].upper()}] {rec['priority'].upper()}")
                    logger.info(f"   问题: {rec['issue']}")
                    logger.info(f"   建议: {rec['suggestion']}")
                    logger.info("")
            else:
                logger.info("✅ 系统运行良好，暂无优化建议")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ 生成优化报告异常: {e}")
            return []
    
    async def run_full_test_suite(self):
        """运行完整测试套件"""
        logger.info("🚀 开始运行百度文心一言完整测试套件")
        logger.info("=" * 60)
        
        test_results = {}
        
        # 1. 初始化测试
        test_results["initialization"] = await self.initialize()
        if not test_results["initialization"]:
            logger.error("❌ 初始化失败，终止测试")
            return test_results
        
        # 2. 连接测试
        test_results["connection"] = await self.test_connection()
        
        # 3. 基础功能测试
        test_results["basic_chat"] = await self.test_basic_chat()
        test_results["streaming_chat"] = await self.test_streaming_chat()
        test_results["model_recommendation"] = await self.test_model_recommendation()
        test_results["chinese_optimization"] = await self.test_chinese_optimization()
        test_results["cost_calculation"] = await self.test_cost_calculation()
        
        # 4. 性能测试
        performance_results = await self.performance_benchmark()
        test_results["performance"] = bool(performance_results)
        
        # 5. 生成报告
        optimization_recommendations = await self.generate_optimization_report()
        
        # 汇总结果
        logger.info("\n📋 测试结果汇总:")
        logger.info("=" * 40)
        
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"{test_name.replace('_', ' ').title():<25} {status}")
        
        logger.info("-" * 40)
        logger.info(f"总体结果: {passed_tests}/{total_tests} 测试通过 ({passed_tests/total_tests:.1%})")
        
        if passed_tests == total_tests:
            logger.info("🎉 所有测试通过！百度文心一言集成已就绪")
        elif passed_tests >= total_tests * 0.8:
            logger.info("⚠️ 大部分测试通过，系统基本可用")
        else:
            logger.info("❌ 多项测试失败，请检查配置和网络连接")
        
        return test_results


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="百度文心一言集成初始化脚本")
    parser.add_argument("--api-key", required=True, help="百度API Key")
    parser.add_argument("--secret-key", required=True, help="百度Secret Key")
    parser.add_argument("--environment", default="production", 
                       choices=["production", "sandbox", "development"],
                       help="运行环境")
    parser.add_argument("--test-type", default="full",
                       choices=["full", "basic", "performance", "connection"],
                       help="测试类型")
    parser.add_argument("--output", help="结果输出文件")
    
    args = parser.parse_args()
    
    # 创建初始化器
    initializer = BaiduWenxinInitializer(
        api_key=args.api_key,
        secret_key=args.secret_key,
        environment=args.environment
    )
    
    try:
        if args.test_type == "full":
            results = await initializer.run_full_test_suite()
        elif args.test_type == "basic":
            await initializer.initialize()
            results = {
                "connection": await initializer.test_connection(),
                "basic_chat": await initializer.test_basic_chat()
            }
        elif args.test_type == "performance":
            await initializer.initialize()
            results = await initializer.performance_benchmark()
        elif args.test_type == "connection":
            await initializer.initialize()
            results = {"connection": await initializer.test_connection()}
        
        # 保存结果到文件
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"测试结果已保存到: {args.output}")
        
        # 返回退出码
        if isinstance(results, dict):
            if all(results.values()):
                return 0  # 所有测试通过
            elif any(results.values()):
                return 1  # 部分测试通过
            else:
                return 2  # 所有测试失败
        else:
            return 0 if results else 2
            
    except KeyboardInterrupt:
        logger.info("用户中断测试")
        return 130
    except Exception as e:
        logger.error(f"测试过程中发生异常: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)