#!/usr/bin/env python3
"""
仪表板管理模块测试执行脚本
简化的测试执行入口，支持不同测试模式
"""

import asyncio
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DashboardTestRunner:
    """仪表板测试运行器"""
    
    def __init__(self):
        self.config = self._load_test_config()
        self.base_url = self.config.get("dashboard_integration_tests", {}).get("base_url", "http://localhost:8000")
        
    def _load_test_config(self) -> Dict[str, Any]:
        """加载测试配置"""
        try:
            config_path = Path(__file__).parent / "test_config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)["test_configuration"]
            else:
                logger.warning("测试配置文件不存在，使用默认配置")
                return {}
        except Exception as e:
            logger.error(f"加载测试配置失败: {str(e)}")
            return {}
    
    async def run_smoke_test(self) -> bool:
        """运行快速冒烟测试"""
        logger.info("🚀 开始运行快速冒烟测试...")
        
        try:
            from run_comprehensive_dashboard_integration_tests import ComprehensiveDashboardIntegrationTestRunner
            
            test_runner = ComprehensiveDashboardIntegrationTestRunner(self.base_url)
            success, results = await test_runner.run_quick_smoke_test()
            
            if success:
                logger.info("✅ 冒烟测试通过")
            else:
                logger.error("❌ 冒烟测试失败")
                logger.error(f"失败详情: {results}")
            
            return success
            
        except Exception as e:
            logger.error(f"冒烟测试执行异常: {str(e)}")
            return False
    
    async def run_system_integration_test(self) -> bool:
        """运行系统集成测试"""
        logger.info("🔧 开始运行系统集成测试...")
        
        try:
            from test_dashboard_system_integration import DashboardSystemIntegrationTest
            
            test_suite = DashboardSystemIntegrationTest()
            success, results = await test_suite.run_all_tests()
            
            if success:
                logger.info("✅ 系统集成测试通过")
            else:
                logger.error("❌ 系统集成测试失败")
                logger.error(f"失败详情: {results}")
            
            return success
            
        except Exception as e:
            logger.error(f"系统集成测试执行异常: {str(e)}")
            return False
    
    async def run_performance_test(self) -> bool:
        """运行性能测试"""
        logger.info("⚡ 开始运行性能测试...")
        
        try:
            from test_dashboard_performance_load import DashboardPerformanceLoadTest
            
            performance_test = DashboardPerformanceLoadTest(self.base_url)
            success, results = await performance_test.run_comprehensive_performance_test()
            
            if success:
                logger.info("✅ 性能测试通过")
            else:
                logger.error("❌ 性能测试失败")
                logger.error(f"失败详情: {results}")
            
            return success
            
        except Exception as e:
            logger.error(f"性能测试执行异常: {str(e)}")
            return False
    
    async def run_security_test(self) -> bool:
        """运行安全测试"""
        logger.info("🔒 开始运行安全测试...")
        
        try:
            from test_dashboard_security_compatibility import DashboardSecurityCompatibilityTest
            
            security_test = DashboardSecurityCompatibilityTest(self.base_url)
            success, results = await security_test.run_comprehensive_security_compatibility_test()
            
            if success:
                logger.info("✅ 安全测试通过")
            else:
                logger.error("❌ 安全测试失败")
                logger.error(f"失败详情: {results}")
            
            return success
            
        except Exception as e:
            logger.error(f"安全测试执行异常: {str(e)}")
            return False
    
    async def run_full_integration_test(self) -> bool:
        """运行完整集成测试"""
        logger.info("🎯 开始运行完整集成测试...")
        
        try:
            from run_comprehensive_dashboard_integration_tests import ComprehensiveDashboardIntegrationTestRunner
            
            test_runner = ComprehensiveDashboardIntegrationTestRunner(self.base_url)
            success, results = await test_runner.run_all_integration_tests()
            
            if success:
                logger.info("✅ 完整集成测试通过")
            else:
                logger.error("❌ 完整集成测试失败")
            
            return success
            
        except Exception as e:
            logger.error(f"完整集成测试执行异常: {str(e)}")
            return False
    
    def print_usage(self):
        """打印使用说明"""
        print("""
仪表板管理模块测试执行脚本

使用方法:
    python run_dashboard_tests.py [测试类型]

测试类型:
    smoke       - 快速冒烟测试（检查基本功能）
    system      - 系统集成测试（完整性和稳定性）
    performance - 性能和负载测试
    security    - 安全性和兼容性测试
    full        - 完整集成测试（包含所有测试）
    
示例:
    python run_dashboard_tests.py smoke
    python run_dashboard_tests.py system
    python run_dashboard_tests.py full

配置:
    测试配置文件: test_config.json
    默认测试URL: http://localhost:8000
        """)

async def main():
    """主函数"""
    runner = DashboardTestRunner()
    
    if len(sys.argv) < 2:
        runner.print_usage()
        sys.exit(1)
    
    test_type = sys.argv[1].lower()
    
    logger.info("=" * 80)
    logger.info("🧪 仪表板管理模块测试执行器")
    logger.info(f"📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🎯 测试类型: {test_type}")
    logger.info(f"🌐 测试目标: {runner.base_url}")
    logger.info("=" * 80)
    
    success = False
    
    try:
        if test_type == "smoke":
            success = await runner.run_smoke_test()
        elif test_type == "system":
            success = await runner.run_system_integration_test()
        elif test_type == "performance":
            success = await runner.run_performance_test()
        elif test_type == "security":
            success = await runner.run_security_test()
        elif test_type == "full":
            success = await runner.run_full_integration_test()
        else:
            logger.error(f"❌ 未知的测试类型: {test_type}")
            runner.print_usage()
            sys.exit(1)
        
        logger.info("=" * 80)
        if success:
            logger.info("🎉 测试执行成功！")
            logger.info("✅ 所有测试都通过了验收标准")
        else:
            logger.error("❌ 测试执行失败！")
            logger.error("🔍 请查看详细日志和报告文件")
        logger.info("=" * 80)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("⏹️  测试被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 测试执行异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())