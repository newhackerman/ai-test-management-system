#!/usr/bin/env python3
"""
阿里通义千问服务初始化脚本

本脚本用于初始化和测试阿里通义千问服务，包括：
1. 验证API密钥
2. 测试连接
3. 检查模型可用性
4. 运行性能测试
5. 验证中文优化功能

使用方法:
    python init_aliyun_tongyi.py --api-key YOUR_API_KEY --test-type connection
    python init_aliyun_tongyi.py --api-key YOUR_API_KEY --test-type full
    python init_aliyun_tongyi.py --api-key YOUR_API_KEY --test-type performance
"""

import argparse
import asyncio
import logging
import sys
import time
from typing import Dict, Any, List
import json

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_connection(api_key: str) -> bool:
    """测试连接"""
    logger.info("🔗 测试阿里通义千问连接...")
    
    try:
        from ..services.aliyun_tongyi_service import initialize_tongyi_service
        from ..adapters.base import ChatMessage, MessageRole
        
        # 初始化服务
        service = await initialize_tongyi_service(api_key=api_key)
        
        # 发送测试消息
        messages = [
            ChatMessage(role=MessageRole.USER, content="你好，请简单介绍一下你自己")
        ]
        
        response = await service.chat_completion(
            messages=messages,
            user_id=1,
            model="qwen-turbo",
            max_tokens=100
        )
        
        if response.success:
            logger.info("✅ 连接测试成功")
            logger.info(f"   模型: {response.model}")
            logger.info(f"   响应时间: {response.response_time:.2f}秒")
            logger.info(f"   Token使用: {response.usage.total_tokens if response.usage else 0}")
            logger.info(f"   回复内容: {response.content[:100]}...")
            return True
        else:
            logger.error(f"❌ 连接测试失败: {response.error_message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 连接测试异常: {e}")
        return False


async def test_models(api_key: str) -> Dict[str, Any]:
    """测试模型可用性"""
    logger.info("🤖 测试模型可用性...")
    
    try:
        from ..services.aliyun_tongyi_service import initialize_tongyi_service
        from ..adapters.base import ChatMessage, MessageRole
        
        service = await initialize_tongyi_service(api_key=api_key)
        
        if not service.adapter:
            logger.error("❌ 服务适配器未初始化")
            return {"success": False, "models": []}
        
        # 获取可用模型
        available_models = await service.adapter.get_available_models()
        logger.info(f"✅ 发现 {len(available_models)} 个可用模型")
        
        # 测试每个模型
        model_results = {}
        test_message = "你好"
        
        for model in available_models[:4]:  # 测试前4个模型
            try:
                logger.info(f"   测试模型: {model}")
                
                messages = [ChatMessage(role=MessageRole.USER, content=test_message)]
                
                start_time = time.time()
                response = await service.chat_completion(
                    messages=messages,
                    user_id=1,
                    model=model,
                    max_tokens=50
                )
                end_time = time.time()
                
                if response.success:
                    model_results[model] = {
                        "success": True,
                        "response_time": end_time - start_time,
                        "tokens_used": response.usage.total_tokens if response.usage else 0,
                        "content_length": len(response.content)
                    }
                    logger.info(f"     ✅ 成功 - {end_time - start_time:.2f}秒")
                else:
                    model_results[model] = {
                        "success": False,
                        "error": response.error_message
                    }
                    logger.warning(f"     ❌ 失败 - {response.error_message}")
                
                # 避免请求过于频繁
                await asyncio.sleep(1)
                
            except Exception as e:
                model_results[model] = {
                    "success": False,
                    "error": str(e)
                }
                logger.warning(f"     ❌ 异常 - {e}")
        
        return {
            "success": True,
            "available_models": available_models,
            "model_results": model_results
        }
        
    except Exception as e:
        logger.error(f"❌ 模型测试异常: {e}")
        return {"success": False, "error": str(e)}


async def test_streaming(api_key: str) -> bool:
    """测试流式响应"""
    logger.info("🌊 测试流式响应...")
    
    try:
        from ..services.aliyun_tongyi_service import initialize_tongyi_service
        from ..adapters.base import ChatMessage, MessageRole
        
        service = await initialize_tongyi_service(api_key=api_key)
        
        messages = [
            ChatMessage(role=MessageRole.USER, content="请数从1到10")
        ]
        
        chunks_received = 0
        total_content = ""
        
        start_time = time.time()
        
        async for chunk in service.stream_chat_completion(
            messages=messages,
            user_id=1,
            model="qwen-turbo"
        ):
            chunks_received += 1
            total_content += chunk.content
            
            if chunk.is_final:
                break
        
        end_time = time.time()
        
        if chunks_received > 0:
            logger.info("✅ 流式响应测试成功")
            logger.info(f"   接收块数: {chunks_received}")
            logger.info(f"   总时间: {end_time - start_time:.2f}秒")
            logger.info(f"   内容长度: {len(total_content)}字符")
            logger.info(f"   内容预览: {total_content[:100]}...")
            return True
        else:
            logger.error("❌ 流式响应测试失败: 未接收到数据块")
            return False
            
    except Exception as e:
        logger.error(f"❌ 流式响应测试异常: {e}")
        return False


async def test_chinese_optimization(api_key: str) -> Dict[str, Any]:
    """测试中文优化功能"""
    logger.info("🇨🇳 测试中文优化功能...")
    
    try:
        from ..services.aliyun_tongyi_service import initialize_tongyi_service
        from ..adapters.base import ChatMessage, MessageRole
        
        service = await initialize_tongyi_service(api_key=api_key)
        
        # 测试英文输入中文输出
        english_messages = [
            ChatMessage(role=MessageRole.USER, content="Hello, please introduce yourself briefly.")
        ]
        
        response = await service.chat_completion(
            messages=english_messages,
            user_id=1,
            model="qwen-plus"
        )
        
        if response.success:
            content = response.content
            
            # 分析中文特征
            chinese_chars = sum(1 for char in content if '\u4e00' <= char <= '\u9fff')
            total_chars = len(content)
            chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
            
            # 检查中文标点
            chinese_punctuation = ["。", "，", "？", "！", "；", "："]
            has_chinese_punct = any(punct in content for punct in chinese_punctuation)
            
            # 检查礼貌用语
            polite_words = ["您好", "请", "谢谢", "不好意思", "很高兴"]
            has_polite_words = any(word in content for word in polite_words)
            
            logger.info("✅ 中文优化测试完成")
            logger.info(f"   中文字符比例: {chinese_ratio:.1%}")
            logger.info(f"   使用中文标点: {'是' if has_chinese_punct else '否'}")
            logger.info(f"   包含礼貌用语: {'是' if has_polite_words else '否'}")
            logger.info(f"   回复内容: {content[:150]}...")
            
            return {
                "success": True,
                "chinese_ratio": chinese_ratio,
                "has_chinese_punctuation": has_chinese_punct,
                "has_polite_words": has_polite_words,
                "content": content
            }
        else:
            logger.error(f"❌ 中文优化测试失败: {response.error_message}")
            return {"success": False, "error": response.error_message}
            
    except Exception as e:
        logger.error(f"❌ 中文优化测试异常: {e}")
        return {"success": False, "error": str(e)}


async def test_model_recommendation(api_key: str) -> Dict[str, Any]:
    """测试模型推荐功能"""
    logger.info("🎯 测试模型推荐功能...")
    
    try:
        from ..services.aliyun_tongyi_service import initialize_tongyi_service
        
        service = await initialize_tongyi_service(api_key=api_key)
        
        test_tasks = [
            "你好",
            "请解释一下机器学习的基本概念",
            "请设计一个完整的微服务架构，包括服务发现、负载均衡、熔断器等组件"
        ]
        
        recommendation_results = {}
        
        for task in test_tasks:
            try:
                recommendations = await service.get_model_recommendations(task)
                
                if recommendations:
                    best_rec = recommendations[0]
                    recommendation_results[task] = {
                        "recommended_model": best_rec.recommended_model.value,
                        "confidence": best_rec.confidence,
                        "reasoning": best_rec.reasoning,
                        "estimated_cost": best_rec.estimated_cost,
                        "estimated_time": best_rec.estimated_time
                    }
                    
                    logger.info(f"   任务: {task[:30]}...")
                    logger.info(f"     推荐模型: {best_rec.recommended_model.value}")
                    logger.info(f"     置信度: {best_rec.confidence:.2f}")
                    logger.info(f"     预估成本: {best_rec.estimated_cost:.4f}元")
                
            except Exception as e:
                logger.warning(f"   任务推荐失败: {task[:30]}... - {e}")
                recommendation_results[task] = {"error": str(e)}
        
        logger.info("✅ 模型推荐测试完成")
        
        return {
            "success": True,
            "recommendations": recommendation_results
        }
        
    except Exception as e:
        logger.error(f"❌ 模型推荐测试异常: {e}")
        return {"success": False, "error": str(e)}


async def performance_test(api_key: str) -> Dict[str, Any]:
    """性能测试"""
    logger.info("⚡ 运行性能测试...")
    
    try:
        from ..services.aliyun_tongyi_service import initialize_tongyi_service
        from ..adapters.base import ChatMessage, MessageRole
        
        service = await initialize_tongyi_service(api_key=api_key)
        
        # 测试参数
        test_models = ["qwen-turbo", "qwen-plus"]
        test_message = "请简单介绍一下人工智能"
        concurrent_requests = 3
        
        performance_results = {}
        
        for model in test_models:
            logger.info(f"   测试模型: {model}")
            
            # 并发测试
            tasks = []
            for i in range(concurrent_requests):
                messages = [ChatMessage(role=MessageRole.USER, content=f"{test_message} (请求{i+1})")]
                task = service.chat_completion(
                    messages=messages,
                    user_id=i+1,
                    model=model,
                    max_tokens=200
                )
                tasks.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # 分析结果
            successful_responses = [r for r in responses if not isinstance(r, Exception) and r.success]
            failed_responses = [r for r in responses if isinstance(r, Exception) or not r.success]
            
            if successful_responses:
                avg_response_time = sum(r.response_time for r in successful_responses) / len(successful_responses)
                total_tokens = sum(r.usage.total_tokens if r.usage else 0 for r in successful_responses)
                
                performance_results[model] = {
                    "concurrent_requests": concurrent_requests,
                    "successful_requests": len(successful_responses),
                    "failed_requests": len(failed_responses),
                    "total_time": end_time - start_time,
                    "avg_response_time": avg_response_time,
                    "total_tokens": total_tokens,
                    "requests_per_second": concurrent_requests / (end_time - start_time)
                }
                
                logger.info(f"     成功请求: {len(successful_responses)}/{concurrent_requests}")
                logger.info(f"     平均响应时间: {avg_response_time:.2f}秒")
                logger.info(f"     总耗时: {end_time - start_time:.2f}秒")
                logger.info(f"     QPS: {concurrent_requests / (end_time - start_time):.2f}")
            else:
                performance_results[model] = {
                    "error": "所有请求都失败了"
                }
                logger.warning(f"     ❌ 所有请求都失败了")
        
        logger.info("✅ 性能测试完成")
        
        return {
            "success": True,
            "results": performance_results
        }
        
    except Exception as e:
        logger.error(f"❌ 性能测试异常: {e}")
        return {"success": False, "error": str(e)}


async def full_test(api_key: str) -> Dict[str, Any]:
    """完整测试"""
    logger.info("🧪 运行完整测试套件...")
    
    results = {
        "connection": False,
        "models": {},
        "streaming": False,
        "chinese_optimization": {},
        "model_recommendation": {},
        "performance": {}
    }
    
    try:
        # 1. 连接测试
        results["connection"] = await test_connection(api_key)
        
        if not results["connection"]:
            logger.error("❌ 连接测试失败，跳过后续测试")
            return results
        
        # 2. 模型测试
        results["models"] = await test_models(api_key)
        
        # 3. 流式响应测试
        results["streaming"] = await test_streaming(api_key)
        
        # 4. 中文优化测试
        results["chinese_optimization"] = await test_chinese_optimization(api_key)
        
        # 5. 模型推荐测试
        results["model_recommendation"] = await test_model_recommendation(api_key)
        
        # 6. 性能测试
        results["performance"] = await performance_test(api_key)
        
        # 生成测试报告
        logger.info("\n" + "="*50)
        logger.info("📊 测试报告")
        logger.info("="*50)
        
        logger.info(f"连接测试: {'✅ 通过' if results['connection'] else '❌ 失败'}")
        logger.info(f"模型测试: {'✅ 通过' if results['models'].get('success') else '❌ 失败'}")
        logger.info(f"流式响应: {'✅ 通过' if results['streaming'] else '❌ 失败'}")
        logger.info(f"中文优化: {'✅ 通过' if results['chinese_optimization'].get('success') else '❌ 失败'}")
        logger.info(f"模型推荐: {'✅ 通过' if results['model_recommendation'].get('success') else '❌ 失败'}")
        logger.info(f"性能测试: {'✅ 通过' if results['performance'].get('success') else '❌ 失败'}")
        
        # 计算总体成功率
        total_tests = 6
        passed_tests = sum([
            results["connection"],
            results["models"].get("success", False),
            results["streaming"],
            results["chinese_optimization"].get("success", False),
            results["model_recommendation"].get("success", False),
            results["performance"].get("success", False)
        ])
        
        success_rate = passed_tests / total_tests
        logger.info(f"\n总体成功率: {success_rate:.1%} ({passed_tests}/{total_tests})")
        
        if success_rate >= 0.8:
            logger.info("🎉 阿里通义千问服务集成测试通过！")
        else:
            logger.warning("⚠️  部分测试失败，请检查配置和网络连接")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 完整测试异常: {e}")
        results["error"] = str(e)
        return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="阿里通义千问服务初始化和测试")
    parser.add_argument("--api-key", required=True, help="阿里云API密钥")
    parser.add_argument("--test-type", choices=["connection", "models", "streaming", "chinese", "recommendation", "performance", "full"], 
                       default="connection", help="测试类型")
    parser.add_argument("--output", help="输出结果到JSON文件")
    
    args = parser.parse_args()
    
    async def run_test():
        logger.info(f"🚀 开始阿里通义千问 {args.test_type} 测试")
        logger.info(f"API密钥: {args.api_key[:8]}...{args.api_key[-4:]}")
        
        try:
            if args.test_type == "connection":
                result = await test_connection(args.api_key)
            elif args.test_type == "models":
                result = await test_models(args.api_key)
            elif args.test_type == "streaming":
                result = await test_streaming(args.api_key)
            elif args.test_type == "chinese":
                result = await test_chinese_optimization(args.api_key)
            elif args.test_type == "recommendation":
                result = await test_model_recommendation(args.api_key)
            elif args.test_type == "performance":
                result = await performance_test(args.api_key)
            elif args.test_type == "full":
                result = await full_test(args.api_key)
            else:
                logger.error(f"未知的测试类型: {args.test_type}")
                return False
            
            # 输出结果
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                logger.info(f"测试结果已保存到: {args.output}")
            
            return result
            
        except Exception as e:
            logger.error(f"测试执行失败: {e}")
            return False
    
    # 运行测试
    result = asyncio.run(run_test())
    
    # 设置退出码
    if isinstance(result, bool):
        sys.exit(0 if result else 1)
    elif isinstance(result, dict):
        if args.test_type == "full":
            # 完整测试的成功判断
            success_count = sum([
                result.get("connection", False),
                result.get("models", {}).get("success", False),
                result.get("streaming", False),
                result.get("chinese_optimization", {}).get("success", False),
                result.get("model_recommendation", {}).get("success", False),
                result.get("performance", {}).get("success", False)
            ])
            sys.exit(0 if success_count >= 4 else 1)  # 至少4个测试通过
        else:
            sys.exit(0 if result.get("success", False) else 1)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()