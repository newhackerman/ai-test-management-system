"""
缓存预热初始化脚本

本脚本用于初始化和启动缓存预热机制，包括：
1. 初始化预热服务
2. 启动预热调度器
3. 配置预热策略
4. 执行初始预热

使用方法：
python -m backend.src.scripts.init_cache_preheating
"""
import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.src.services.cache_preheating_service import (
    get_cache_preheating_service,
    start_cache_preheating
)
from backend.src.tasks.cache_preheating_scheduler import (
    get_cache_preheating_scheduler,
    start_cache_preheating_scheduler,
    preheat_user_data,
    preheat_popular_data
)
from backend.src.core.config import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def init_cache_preheating():
    """初始化缓存预热机制"""
    try:
        logger.info("开始初始化缓存预热机制...")
        
        # 1. 初始化预热服务
        logger.info("初始化预热服务...")
        preheating_service = await get_cache_preheating_service()
        logger.info("预热服务初始化完成")
        
        # 2. 初始化调度器
        logger.info("初始化预热调度器...")
        scheduler = await get_cache_preheating_scheduler()
        logger.info("预热调度器初始化完成")
        
        # 3. 启动预热工作进程
        logger.info("启动预热工作进程...")
        await start_cache_preheating()
        logger.info("预热工作进程启动完成")
        
        # 4. 启动调度器
        logger.info("启动预热调度器...")
        await start_cache_preheating_scheduler()
        logger.info("预热调度器启动完成")
        
        # 5. 执行初始预热
        logger.info("执行初始预热...")
        await perform_initial_preheating()
        logger.info("初始预热完成")
        
        logger.info("缓存预热机制初始化成功！")
        
        # 6. 显示状态信息
        await show_preheating_status(preheating_service, scheduler)
        
    except Exception as e:
        logger.error(f"缓存预热机制初始化失败: {e}")
        raise


async def perform_initial_preheating():
    """执行初始预热"""
    try:
        # 预热热门数据
        logger.info("预热热门数据...")
        await preheat_popular_data()
        
        # 预热用户数据（前5个活跃用户）
        logger.info("预热活跃用户数据...")
        await preheat_user_data(limit=10)
        
        logger.info("初始预热任务已提交")
        
    except Exception as e:
        logger.warning(f"初始预热执行失败: {e}")


async def show_preheating_status(preheating_service, scheduler):
    """显示预热状态信息"""
    try:
        # 获取预热服务状态
        status = await preheating_service.get_preheating_status()
        
        # 获取调度器任务状态
        jobs = scheduler.get_job_status()
        
        logger.info("=== 缓存预热状态 ===")
        logger.info(f"预热服务状态: {'启用' if status['enabled'] else '禁用'}")
        logger.info(f"运行中任务: {status['running_tasks']}")
        logger.info(f"队列中任务: {status['queued_tasks']}")
        logger.info(f"已完成任务: {status['completed_tasks']}")
        logger.info(f"访问模式数量: {status['access_patterns']}")
        
        logger.info("=== 统计信息 ===")
        stats = status['statistics']
        logger.info(f"总任务数: {stats['total_tasks']}")
        logger.info(f"成功任务数: {stats['successful_tasks']}")
        logger.info(f"失败任务数: {stats['failed_tasks']}")
        
        if stats['total_tasks'] > 0:
            success_rate = stats['successful_tasks'] / stats['total_tasks'] * 100
            logger.info(f"成功率: {success_rate:.1f}%")
        
        logger.info("=== 调度任务 ===")
        for job in jobs:
            logger.info(f"任务: {job['name']} (ID: {job['id']})")
            if job['next_run']:
                logger.info(f"  下次运行: {job['next_run']}")
            logger.info(f"  触发器: {job['trigger']}")
        
    except Exception as e:
        logger.warning(f"获取状态信息失败: {e}")


async def test_preheating_functionality():
    """测试预热功能"""
    try:
        logger.info("=== 测试预热功能 ===")
        
        # 获取预热服务
        service = await get_cache_preheating_service()
        
        # 测试手动预热
        logger.info("测试手动预热...")
        task_id = await service.manual_preheat(
            "ai_model_configs",
            {}
        )
        logger.info(f"手动预热任务已创建: {task_id}")
        
        # 等待任务执行
        await asyncio.sleep(2)
        
        # 检查任务状态
        status = await service.get_preheating_status()
        logger.info(f"任务执行后状态 - 总任务: {status['statistics']['total_tasks']}")
        
        # 测试访问模式分析
        logger.info("测试访问模式分析...")
        await service.analyze_access_patterns()
        
        status = await service.get_preheating_status()
        logger.info(f"访问模式数量: {status['access_patterns']}")
        
        logger.info("预热功能测试完成")
        
    except Exception as e:
        logger.error(f"预热功能测试失败: {e}")


async def cleanup_preheating():
    """清理预热资源"""
    try:
        logger.info("清理预热资源...")
        
        # 停止调度器
        from backend.src.tasks.cache_preheating_scheduler import stop_cache_preheating_scheduler
        await stop_cache_preheating_scheduler()
        
        # 停止预热服务
        service = await get_cache_preheating_service()
        await service.stop_preheating()
        
        logger.info("预热资源清理完成")
        
    except Exception as e:
        logger.warning(f"清理预热资源失败: {e}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="缓存预热初始化脚本")
    parser.add_argument("--test", action="store_true", help="运行功能测试")
    parser.add_argument("--status", action="store_true", help="只显示状态信息")
    parser.add_argument("--cleanup", action="store_true", help="清理预热资源")
    
    args = parser.parse_args()
    
    try:
        if args.cleanup:
            await cleanup_preheating()
        elif args.status:
            # 只显示状态
            service = await get_cache_preheating_service()
            scheduler = await get_cache_preheating_scheduler()
            await show_preheating_status(service, scheduler)
        elif args.test:
            # 初始化并测试
            await init_cache_preheating()
            await test_preheating_functionality()
        else:
            # 正常初始化
            await init_cache_preheating()
            
            # 保持运行一段时间以观察效果
            logger.info("预热机制运行中，按Ctrl+C停止...")
            try:
                await asyncio.sleep(60)  # 运行1分钟
            except KeyboardInterrupt:
                logger.info("收到停止信号")
            
            await cleanup_preheating()
    
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        await cleanup_preheating()
    except Exception as e:
        logger.error(f"脚本执行失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)