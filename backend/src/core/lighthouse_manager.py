"""
Lighthouse性能监控管理器

本模块提供Web性能分析功能，包括：
- Lighthouse性能审计
- 性能指标收集
- 历史数据存储
- 性能对比分析
"""
import asyncio
import json
import uuid
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from ..models.infrastructure import LighthouseResult
from ..core.database import get_async_session

logger = logging.getLogger(__name__)


@dataclass
class LighthouseConfig:
    """Lighthouse配置"""
    mobile: bool = False
    throttling: bool = True
    categories: List[str] = None
    output_format: str = 'json'
    chrome_flags: List[str] = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = ['performance', 'accessibility', 'best-practices', 'seo']
        if self.chrome_flags is None:
            self.chrome_flags = ['--headless', '--no-sandbox', '--disable-dev-shm-usage']


@dataclass
class PerformanceMetrics:
    """性能指标"""
    first_contentful_paint: float = 0.0
    largest_contentful_paint: float = 0.0
    cumulative_layout_shift: float = 0.0
    first_input_delay: float = 0.0
    speed_index: float = 0.0
    total_blocking_time: float = 0.0
    time_to_interactive: float = 0.0


@dataclass
class PerformanceScores:
    """性能评分"""
    performance: int = 0
    accessibility: int = 0
    best_practices: int = 0
    seo: int = 0
    pwa: int = 0


@dataclass
class PerformanceOpportunity:
    """性能优化建议"""
    title: str
    description: str
    potential_savings: float
    audit_id: str
    score_display_mode: str = 'numeric'


@dataclass
class LighthouseAuditResult:
    """Lighthouse审计结果"""
    audit_id: str
    url: str
    metrics: PerformanceMetrics
    scores: PerformanceScores
    opportunities: List[PerformanceOpportunity]
    raw_data: Dict[str, Any]
    created_at: datetime
    device_type: str = 'desktop'
    lighthouse_version: str = ''
    user_agent: str = ''


class LighthouseManager:
    """Lighthouse性能监控管理器"""
    
    def __init__(self, db_session: AsyncSession = None):
        self.db = db_session
        self.reports_dir = Path('lighthouse_reports')
        self.reports_dir.mkdir(exist_ok=True)
        self.lighthouse_cmd = self._get_lighthouse_command()
        
    def _get_lighthouse_command(self) -> str:
        """获取Lighthouse命令路径"""
        import platform
        
        # Windows环境下的处理
        if platform.system() == 'Windows':
            # 尝试直接使用lighthouse命令
            try:
                result = os.system('lighthouse --version >nul 2>&1')
                if result == 0:
                    return 'lighthouse'
            except:
                pass
            
            # 尝试npx lighthouse
            try:
                result = os.system('npx lighthouse --version >nul 2>&1')
                if result == 0:
                    return 'npx lighthouse'
            except:
                pass
        else:
            # Linux/Mac环境下的处理
            if os.system('which lighthouse > /dev/null 2>&1') == 0:
                return 'lighthouse'
            
            if os.system('which npx > /dev/null 2>&1') == 0:
                return 'npx lighthouse'
        
        # 如果都没有找到，返回默认命令
        logger.warning("Lighthouse not found. Please install with: npm install -g lighthouse")
        return 'lighthouse'
    
    async def run_audit(self, url: str, config: LighthouseConfig = None) -> LighthouseAuditResult:
        """运行Lighthouse性能审计"""
        if config is None:
            config = LighthouseConfig()
        
        audit_id = str(uuid.uuid4())
        report_path = self.reports_dir / f'{audit_id}.json'
        
        try:
            # 构建Lighthouse命令
            cmd = self._build_lighthouse_command(url, report_path, config)
            
            logger.info(f"Running Lighthouse audit for {url}")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            # 执行Lighthouse命令
            import platform
            if platform.system() == 'Windows':
                # Windows环境下使用shell模式
                cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd)
                process = await asyncio.create_subprocess_shell(
                    cmd_str,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                # Linux/Mac环境下使用exec模式
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Lighthouse execution failed: {error_msg}")
                raise Exception(f"Lighthouse执行失败: {error_msg}")
            
            # 解析结果
            if not report_path.exists():
                raise Exception("Lighthouse报告文件未生成")
            
            with open(report_path, 'r', encoding='utf-8') as f:
                lighthouse_data = json.load(f)
            
            result = await self._parse_lighthouse_results(lighthouse_data, audit_id, url, config)
            
            # 保存到数据库
            if self.db:
                await self._save_audit_result(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Performance audit failed for {url}: {e}")
            raise Exception(f"性能审计失败: {str(e)}")
        finally:
            # 清理临时文件
            if report_path.exists():
                try:
                    report_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup report file: {e}")
    
    def _build_lighthouse_command(self, url: str, report_path: Path, config: LighthouseConfig) -> List[str]:
        """构建Lighthouse命令"""
        cmd = [self.lighthouse_cmd, url]
        
        # 输出格式和路径
        cmd.extend(['--output', config.output_format])
        cmd.extend(['--output-path', str(report_path)])
        
        # Chrome标志
        if config.chrome_flags:
            cmd.extend(['--chrome-flags', ' '.join(config.chrome_flags)])
        
        # 设备类型
        if config.mobile:
            cmd.extend(['--preset', 'perf'])
            cmd.extend(['--emulated-form-factor', 'mobile'])
        else:
            cmd.extend(['--emulated-form-factor', 'desktop'])
        
        # 网络节流
        if config.throttling:
            cmd.extend(['--throttling-method', 'simulate'])
        else:
            cmd.extend(['--throttling-method', 'provided'])
        
        # 审计类别
        if config.categories:
            for category in config.categories:
                cmd.extend(['--only-categories', category])
        
        # 静默模式
        cmd.append('--quiet')
        
        return cmd
    
    async def _parse_lighthouse_results(
        self, 
        data: Dict, 
        audit_id: str, 
        url: str, 
        config: LighthouseConfig
    ) -> LighthouseAuditResult:
        """解析Lighthouse结果"""
        categories = data.get('categories', {})
        audits = data.get('audits', {})
        environment = data.get('environment', {})
        
        # 提取核心性能指标
        metrics = PerformanceMetrics(
            first_contentful_paint=self._get_audit_value(audits, 'first-contentful-paint'),
            largest_contentful_paint=self._get_audit_value(audits, 'largest-contentful-paint'),
            cumulative_layout_shift=self._get_audit_value(audits, 'cumulative-layout-shift'),
            first_input_delay=self._get_audit_value(audits, 'max-potential-fid'),
            speed_index=self._get_audit_value(audits, 'speed-index'),
            total_blocking_time=self._get_audit_value(audits, 'total-blocking-time'),
            time_to_interactive=self._get_audit_value(audits, 'interactive')
        )
        
        # 提取评分
        scores = PerformanceScores(
            performance=int((categories.get('performance', {}).get('score', 0) or 0) * 100),
            accessibility=int((categories.get('accessibility', {}).get('score', 0) or 0) * 100),
            best_practices=int((categories.get('best-practices', {}).get('score', 0) or 0) * 100),
            seo=int((categories.get('seo', {}).get('score', 0) or 0) * 100),
            pwa=int((categories.get('pwa', {}).get('score', 0) or 0) * 100)
        )
        
        # 提取优化建议
        opportunities = []
        for audit_key, audit_data in audits.items():
            if audit_data.get('details', {}).get('type') == 'opportunity':
                opportunity = PerformanceOpportunity(
                    title=audit_data.get('title', ''),
                    description=audit_data.get('description', ''),
                    potential_savings=audit_data.get('numericValue', 0),
                    audit_id=audit_key,
                    score_display_mode=audit_data.get('scoreDisplayMode', 'numeric')
                )
                opportunities.append(opportunity)
        
        return LighthouseAuditResult(
            audit_id=audit_id,
            url=url,
            metrics=metrics,
            scores=scores,
            opportunities=opportunities,
            raw_data=data,
            created_at=datetime.utcnow(),
            device_type='mobile' if config.mobile else 'desktop',
            lighthouse_version=environment.get('lighthouseVersion', ''),
            user_agent=environment.get('networkUserAgent', '')
        )
    
    def _get_audit_value(self, audits: Dict, audit_key: str) -> float:
        """获取审计指标值"""
        audit = audits.get(audit_key, {})
        return float(audit.get('numericValue', 0))
    
    async def _save_audit_result(self, result: LighthouseAuditResult):
        """保存审计结果到数据库"""
        try:
            lighthouse_result = LighthouseResult(
                audit_id=result.audit_id,
                url=result.url,
                device_type=result.device_type,
                lighthouse_version=result.lighthouse_version,
                user_agent=result.user_agent,
                
                # 性能指标
                first_contentful_paint=result.metrics.first_contentful_paint,
                largest_contentful_paint=result.metrics.largest_contentful_paint,
                cumulative_layout_shift=result.metrics.cumulative_layout_shift,
                first_input_delay=result.metrics.first_input_delay,
                speed_index=result.metrics.speed_index,
                total_blocking_time=result.metrics.total_blocking_time,
                time_to_interactive=result.metrics.time_to_interactive,
                
                # 评分
                performance_score=result.scores.performance,
                accessibility_score=result.scores.accessibility,
                best_practices_score=result.scores.best_practices,
                seo_score=result.scores.seo,
                pwa_score=result.scores.pwa,
                
                # 优化建议
                opportunities=json.dumps([asdict(opp) for opp in result.opportunities]),
                raw_data=json.dumps(result.raw_data),
                
                created_at=result.created_at
            )
            
            self.db.add(lighthouse_result)
            await self.db.commit()
            
            logger.info(f"Saved Lighthouse audit result: {result.audit_id}")
            
        except Exception as e:
            logger.error(f"Failed to save audit result: {e}")
            await self.db.rollback()
            raise
    
    async def get_performance_history(
        self, 
        url: str, 
        days: int = 30,
        device_type: str = None
    ) -> List[LighthouseAuditResult]:
        """获取性能历史数据"""
        if not self.db:
            return []
        
        try:
            # 构建查询条件
            conditions = [
                LighthouseResult.url == url,
                LighthouseResult.created_at >= datetime.utcnow() - timedelta(days=days)
            ]
            
            if device_type:
                conditions.append(LighthouseResult.device_type == device_type)
            
            # 查询数据库
            stmt = select(LighthouseResult).where(
                and_(*conditions)
            ).order_by(desc(LighthouseResult.created_at))
            
            result = await self.db.execute(stmt)
            records = result.scalars().all()
            
            # 转换为结果对象
            history = []
            for record in records:
                metrics = PerformanceMetrics(
                    first_contentful_paint=record.first_contentful_paint,
                    largest_contentful_paint=record.largest_contentful_paint,
                    cumulative_layout_shift=record.cumulative_layout_shift,
                    first_input_delay=record.first_input_delay,
                    speed_index=record.speed_index,
                    total_blocking_time=record.total_blocking_time,
                    time_to_interactive=record.time_to_interactive
                )
                
                scores = PerformanceScores(
                    performance=record.performance_score,
                    accessibility=record.accessibility_score,
                    best_practices=record.best_practices_score,
                    seo=record.seo_score,
                    pwa=record.pwa_score
                )
                
                opportunities = []
                if record.opportunities:
                    try:
                        opp_data = json.loads(record.opportunities)
                        opportunities = [PerformanceOpportunity(**opp) for opp in opp_data]
                    except Exception as e:
                        logger.warning(f"Failed to parse opportunities: {e}")
                
                raw_data = {}
                if record.raw_data:
                    try:
                        raw_data = json.loads(record.raw_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse raw data: {e}")
                
                audit_result = LighthouseAuditResult(
                    audit_id=record.audit_id,
                    url=record.url,
                    metrics=metrics,
                    scores=scores,
                    opportunities=opportunities,
                    raw_data=raw_data,
                    created_at=record.created_at,
                    device_type=record.device_type,
                    lighthouse_version=record.lighthouse_version,
                    user_agent=record.user_agent
                )
                
                history.append(audit_result)
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get performance history: {e}")
            return []
    
    async def compare_performance(
        self, 
        url: str, 
        baseline_date: datetime,
        comparison_date: datetime = None
    ) -> Dict[str, Any]:
        """性能对比分析"""
        if comparison_date is None:
            comparison_date = datetime.utcnow()
        
        try:
            # 获取基线数据
            baseline_stmt = select(LighthouseResult).where(
                and_(
                    LighthouseResult.url == url,
                    LighthouseResult.created_at >= baseline_date - timedelta(hours=1),
                    LighthouseResult.created_at <= baseline_date + timedelta(hours=1)
                )
            ).order_by(LighthouseResult.created_at.desc()).limit(1)
            
            baseline_result = await self.db.execute(baseline_stmt)
            baseline_record = baseline_result.scalar_one_or_none()
            
            # 获取对比数据
            comparison_stmt = select(LighthouseResult).where(
                and_(
                    LighthouseResult.url == url,
                    LighthouseResult.created_at >= comparison_date - timedelta(hours=1),
                    LighthouseResult.created_at <= comparison_date + timedelta(hours=1)
                )
            ).order_by(LighthouseResult.created_at.desc()).limit(1)
            
            comparison_result = await self.db.execute(comparison_stmt)
            comparison_record = comparison_result.scalar_one_or_none()
            
            if not baseline_record or not comparison_record:
                return {
                    "error": "未找到对比数据",
                    "baseline_found": baseline_record is not None,
                    "comparison_found": comparison_record is not None
                }
            
            # 计算性能变化
            metrics_comparison = {
                "first_contentful_paint": {
                    "baseline": baseline_record.first_contentful_paint,
                    "current": comparison_record.first_contentful_paint,
                    "change": comparison_record.first_contentful_paint - baseline_record.first_contentful_paint,
                    "change_percent": self._calculate_percent_change(
                        baseline_record.first_contentful_paint,
                        comparison_record.first_contentful_paint
                    )
                },
                "largest_contentful_paint": {
                    "baseline": baseline_record.largest_contentful_paint,
                    "current": comparison_record.largest_contentful_paint,
                    "change": comparison_record.largest_contentful_paint - baseline_record.largest_contentful_paint,
                    "change_percent": self._calculate_percent_change(
                        baseline_record.largest_contentful_paint,
                        comparison_record.largest_contentful_paint
                    )
                },
                "speed_index": {
                    "baseline": baseline_record.speed_index,
                    "current": comparison_record.speed_index,
                    "change": comparison_record.speed_index - baseline_record.speed_index,
                    "change_percent": self._calculate_percent_change(
                        baseline_record.speed_index,
                        comparison_record.speed_index
                    )
                }
            }
            
            scores_comparison = {
                "performance": {
                    "baseline": baseline_record.performance_score,
                    "current": comparison_record.performance_score,
                    "change": comparison_record.performance_score - baseline_record.performance_score
                },
                "accessibility": {
                    "baseline": baseline_record.accessibility_score,
                    "current": comparison_record.accessibility_score,
                    "change": comparison_record.accessibility_score - baseline_record.accessibility_score
                },
                "best_practices": {
                    "baseline": baseline_record.best_practices_score,
                    "current": comparison_record.best_practices_score,
                    "change": comparison_record.best_practices_score - baseline_record.best_practices_score
                },
                "seo": {
                    "baseline": baseline_record.seo_score,
                    "current": comparison_record.seo_score,
                    "change": comparison_record.seo_score - baseline_record.seo_score
                }
            }
            
            return {
                "url": url,
                "baseline_date": baseline_record.created_at.isoformat(),
                "comparison_date": comparison_record.created_at.isoformat(),
                "metrics_comparison": metrics_comparison,
                "scores_comparison": scores_comparison,
                "overall_trend": self._analyze_overall_trend(scores_comparison)
            }
            
        except Exception as e:
            logger.error(f"Failed to compare performance: {e}")
            return {"error": f"性能对比分析失败: {str(e)}"}
    
    def _calculate_percent_change(self, baseline: float, current: float) -> float:
        """计算百分比变化"""
        if baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100
    
    def _analyze_overall_trend(self, scores_comparison: Dict) -> str:
        """分析整体趋势"""
        total_change = sum(score["change"] for score in scores_comparison.values())
        
        if total_change > 10:
            return "improved"
        elif total_change < -10:
            return "degraded"
        else:
            return "stable"
    
    async def get_performance_summary(self, url: str, days: int = 7) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            history = await self.get_performance_history(url, days)
            
            if not history:
                return {"error": "没有找到性能数据"}
            
            # 计算平均值
            avg_scores = {
                "performance": sum(h.scores.performance for h in history) / len(history),
                "accessibility": sum(h.scores.accessibility for h in history) / len(history),
                "best_practices": sum(h.scores.best_practices for h in history) / len(history),
                "seo": sum(h.scores.seo for h in history) / len(history)
            }
            
            avg_metrics = {
                "first_contentful_paint": sum(h.metrics.first_contentful_paint for h in history) / len(history),
                "largest_contentful_paint": sum(h.metrics.largest_contentful_paint for h in history) / len(history),
                "speed_index": sum(h.metrics.speed_index for h in history) / len(history),
                "cumulative_layout_shift": sum(h.metrics.cumulative_layout_shift for h in history) / len(history)
            }
            
            # 找出最新和最旧的记录
            latest = history[0]
            oldest = history[-1]
            
            # 计算趋势
            trend = {
                "performance_trend": latest.scores.performance - oldest.scores.performance,
                "fcp_trend": latest.metrics.first_contentful_paint - oldest.metrics.first_contentful_paint,
                "lcp_trend": latest.metrics.largest_contentful_paint - oldest.metrics.largest_contentful_paint
            }
            
            return {
                "url": url,
                "period_days": days,
                "total_audits": len(history),
                "latest_audit": latest.created_at.isoformat(),
                "average_scores": avg_scores,
                "average_metrics": avg_metrics,
                "trend": trend,
                "latest_scores": asdict(latest.scores),
                "latest_metrics": asdict(latest.metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {"error": f"获取性能摘要失败: {str(e)}"}


# 全局实例
lighthouse_manager = None

async def get_lighthouse_manager() -> LighthouseManager:
    """获取Lighthouse管理器实例"""
    global lighthouse_manager
    if lighthouse_manager is None:
        db_session = await get_async_session().__anext__()
        lighthouse_manager = LighthouseManager(db_session)
    return lighthouse_manager