"""
代码覆盖率分析工具

提供详细的代码覆盖率分析、热点识别和改进建议
"""
import ast
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

@dataclass
class FileCoverage:
    """文件覆盖率信息"""
    file_path: str
    lines_total: int
    lines_covered: int
    lines_missing: List[int]
    branches_total: int
    branches_covered: int
    branches_missing: List[Tuple[int, int]]
    functions: List[str]
    functions_covered: List[str]
    complexity_score: float
    
    @property
    def line_coverage_percent(self) -> float:
        return (self.lines_covered / self.lines_total * 100) if self.lines_total > 0 else 0.0
    
    @property
    def branch_coverage_percent(self) -> float:
        return (self.branches_covered / self.branches_total * 100) if self.branches_total > 0 else 0.0
    
    @property
    def function_coverage_percent(self) -> float:
        total_functions = len(self.functions)
        covered_functions = len(self.functions_covered)
        return (covered_functions / total_functions * 100) if total_functions > 0 else 0.0

@dataclass
class CoverageHotspot:
    """覆盖率热点"""
    file_path: str
    line_number: int
    function_name: str
    issue_type: str  # 'uncovered_line', 'uncovered_branch', 'complex_function'
    severity: str    # 'high', 'medium', 'low'
    description: str
    suggestion: str

@dataclass
class CoverageAnalysis:
    """覆盖率分析结果"""
    timestamp: datetime
    overall_coverage: float
    file_coverages: List[FileCoverage]
    hotspots: List[CoverageHotspot]
    recommendations: List[str]
    quality_gates: Dict[str, bool]
    trends: Dict[str, float]

class CoverageAnalyzer:
    """覆盖率分析器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.src_dir = self.project_root / "src"
        self.reports_dir = self.project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # 质量门禁配置
        self.quality_gates = {
            'minimum_line_coverage': 80.0,
            'minimum_branch_coverage': 70.0,
            'minimum_function_coverage': 85.0,
            'maximum_complexity': 10.0,
            'critical_files_coverage': 90.0
        }
        
        # 关键文件模式
        self.critical_file_patterns = [
            '**/models/**/*.py',
            '**/services/**/*.py',
            '**/api/**/*.py',
            '**/core/**/*.py'
        ]
    
    async def analyze_coverage(self, coverage_file: str = None) -> CoverageAnalysis:
        """分析代码覆盖率"""
        logger.info("开始分析代码覆盖率...")
        
        try:
            # 获取覆盖率数据
            coverage_data = await self._get_coverage_data(coverage_file)
            
            # 分析文件覆盖率
            file_coverages = await self._analyze_file_coverages(coverage_data)
            
            # 识别覆盖率热点
            hotspots = await self._identify_hotspots(file_coverages)
            
            # 计算整体覆盖率
            overall_coverage = self._calculate_overall_coverage(file_coverages)
            
            # 检查质量门禁
            quality_gates = self._check_quality_gates(file_coverages, overall_coverage)
            
            # 生成改进建议
            recommendations = self._generate_recommendations(file_coverages, hotspots, quality_gates)
            
            # 获取趋势数据
            trends = await self._get_coverage_trends()
            
            analysis = CoverageAnalysis(
                timestamp=datetime.now(),
                overall_coverage=overall_coverage,
                file_coverages=file_coverages,
                hotspots=hotspots,
                recommendations=recommendations,
                quality_gates=quality_gates,
                trends=trends
            )
            
            # 保存分析结果
            await self._save_analysis(analysis)
            
            logger.info(f"覆盖率分析完成，整体覆盖率: {overall_coverage:.1f}%")
            return analysis
            
        except Exception as e:
            logger.error(f"覆盖率分析失败: {e}")
            raise
    
    async def _get_coverage_data(self, coverage_file: str = None) -> dict:
        """获取覆盖率数据"""
        if coverage_file and Path(coverage_file).exists():
            with open(coverage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 尝试从默认位置获取
        default_coverage_file = self.reports_dir / "coverage.json"
        if default_coverage_file.exists():
            with open(default_coverage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 运行coverage命令生成数据
        logger.info("运行coverage命令生成覆盖率数据...")
        result = subprocess.run([
            sys.executable, '-m', 'coverage', 'json', 
            '--output-file', str(default_coverage_file)
        ], capture_output=True, text=True, cwd=self.project_root)
        
        if result.returncode == 0 and default_coverage_file.exists():
            with open(default_coverage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        logger.warning("无法获取覆盖率数据，返回空数据")
        return {"files": {}, "totals": {}}
    
    async def _analyze_file_coverages(self, coverage_data: dict) -> List[FileCoverage]:
        """分析文件覆盖率"""
        file_coverages = []
        files_data = coverage_data.get('files', {})
        
        for file_path, file_data in files_data.items():
            try:
                # 跳过非源码文件
                if not self._is_source_file(file_path):
                    continue
                
                summary = file_data.get('summary', {})
                
                # 获取函数信息
                functions, functions_covered = await self._analyze_functions(file_path, file_data)
                
                # 计算复杂度
                complexity_score = await self._calculate_complexity(file_path)
                
                file_coverage = FileCoverage(
                    file_path=file_path,
                    lines_total=summary.get('num_statements', 0),
                    lines_covered=summary.get('covered_lines', 0),
                    lines_missing=file_data.get('missing_lines', []),
                    branches_total=summary.get('num_branches', 0),
                    branches_covered=summary.get('covered_branches', 0),
                    branches_missing=file_data.get('missing_branches', []),
                    functions=functions,
                    functions_covered=functions_covered,
                    complexity_score=complexity_score
                )
                
                file_coverages.append(file_coverage)
                
            except Exception as e:
                logger.warning(f"分析文件覆盖率失败 {file_path}: {e}")
        
        return file_coverages
    
    def _is_source_file(self, file_path: str) -> bool:
        """判断是否为源码文件"""
        path = Path(file_path)
        
        # 检查是否在源码目录
        try:
            path.relative_to(self.src_dir)
        except ValueError:
            return False
        
        # 检查文件扩展名
        if path.suffix != '.py':
            return False
        
        # 排除测试文件
        if 'test' in path.name.lower() or 'tests' in str(path).lower():
            return False
        
        # 排除__pycache__等目录
        if '__pycache__' in str(path) or '.pyc' in str(path):
            return False
        
        return True
    
    async def _analyze_functions(self, file_path: str, file_data: dict) -> Tuple[List[str], List[str]]:
        """分析函数覆盖率"""
        functions = []
        functions_covered = []
        
        try:
            # 解析Python文件获取函数定义
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    function_name = node.name
                    functions.append(function_name)
                    
                    # 检查函数是否被覆盖
                    function_start_line = node.lineno
                    function_end_line = getattr(node, 'end_lineno', function_start_line)
                    
                    missing_lines = set(file_data.get('missing_lines', []))
                    function_lines = set(range(function_start_line, function_end_line + 1))
                    
                    # 如果函数的大部分行都被覆盖，认为函数被覆盖
                    covered_lines = function_lines - missing_lines
                    if len(covered_lines) / len(function_lines) > 0.5:
                        functions_covered.append(function_name)
        
        except Exception as e:
            logger.warning(f"分析函数覆盖率失败 {file_path}: {e}")
        
        return functions, functions_covered
    
    async def _calculate_complexity(self, file_path: str) -> float:
        """计算代码复杂度"""
        try:
            # 使用radon计算复杂度
            result = subprocess.run([
                'radon', 'cc', file_path, '--json'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                complexity_data = json.loads(result.stdout)
                file_complexity = complexity_data.get(file_path, [])
                
                if file_complexity:
                    # 计算平均复杂度
                    total_complexity = sum(item.get('complexity', 0) for item in file_complexity)
                    return total_complexity / len(file_complexity)
            
        except Exception as e:
            logger.debug(f"计算复杂度失败 {file_path}: {e}")
        
        # 简单的复杂度估算
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 统计控制流语句
            complexity_keywords = ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'with']
            complexity_score = 1  # 基础复杂度
            
            for keyword in complexity_keywords:
                complexity_score += content.count(f' {keyword} ') + content.count(f'\n{keyword} ')
            
            return complexity_score
            
        except Exception:
            return 1.0
    
    async def _identify_hotspots(self, file_coverages: List[FileCoverage]) -> List[CoverageHotspot]:
        """识别覆盖率热点"""
        hotspots = []
        
        for file_coverage in file_coverages:
            # 识别未覆盖的行
            for line_number in file_coverage.lines_missing[:10]:  # 限制数量
                hotspot = CoverageHotspot(
                    file_path=file_coverage.file_path,
                    line_number=line_number,
                    function_name=await self._get_function_at_line(file_coverage.file_path, line_number),
                    issue_type='uncovered_line',
                    severity=self._determine_severity(file_coverage, 'line'),
                    description=f'第{line_number}行未被测试覆盖',
                    suggestion='添加测试用例覆盖此行代码'
                )
                hotspots.append(hotspot)
            
            # 识别未覆盖的分支
            for branch in file_coverage.branches_missing[:5]:  # 限制数量
                line_number, branch_id = branch
                hotspot = CoverageHotspot(
                    file_path=file_coverage.file_path,
                    line_number=line_number,
                    function_name=await self._get_function_at_line(file_coverage.file_path, line_number),
                    issue_type='uncovered_branch',
                    severity=self._determine_severity(file_coverage, 'branch'),
                    description=f'第{line_number}行的分支{branch_id}未被覆盖',
                    suggestion='添加测试用例覆盖此分支条件'
                )
                hotspots.append(hotspot)
            
            # 识别高复杂度函数
            if file_coverage.complexity_score > self.quality_gates['maximum_complexity']:
                hotspot = CoverageHotspot(
                    file_path=file_coverage.file_path,
                    line_number=1,
                    function_name='整个文件',
                    issue_type='complex_function',
                    severity='high',
                    description=f'文件复杂度过高: {file_coverage.complexity_score:.1f}',
                    suggestion='考虑重构代码，降低复杂度'
                )
                hotspots.append(hotspot)
        
        # 按严重程度排序
        hotspots.sort(key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x.severity])
        
        return hotspots[:50]  # 限制返回数量
    
    async def _get_function_at_line(self, file_path: str, line_number: int) -> str:
        """获取指定行所在的函数名"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start_line = node.lineno
                    end_line = getattr(node, 'end_lineno', start_line)
                    
                    if start_line <= line_number <= end_line:
                        return node.name
            
            return '未知函数'
            
        except Exception:
            return '未知函数'
    
    def _determine_severity(self, file_coverage: FileCoverage, issue_type: str) -> str:
        """确定问题严重程度"""
        # 检查是否为关键文件
        is_critical = any(
            Path(file_coverage.file_path).match(pattern) 
            for pattern in self.critical_file_patterns
        )
        
        if is_critical:
            return 'high'
        
        # 根据覆盖率确定严重程度
        if issue_type == 'line':
            if file_coverage.line_coverage_percent < 50:
                return 'high'
            elif file_coverage.line_coverage_percent < 80:
                return 'medium'
            else:
                return 'low'
        
        elif issue_type == 'branch':
            if file_coverage.branch_coverage_percent < 50:
                return 'high'
            elif file_coverage.branch_coverage_percent < 70:
                return 'medium'
            else:
                return 'low'
        
        return 'medium'
    
    def _calculate_overall_coverage(self, file_coverages: List[FileCoverage]) -> float:
        """计算整体覆盖率"""
        if not file_coverages:
            return 0.0
        
        total_lines = sum(fc.lines_total for fc in file_coverages)
        covered_lines = sum(fc.lines_covered for fc in file_coverages)
        
        return (covered_lines / total_lines * 100) if total_lines > 0 else 0.0
    
    def _check_quality_gates(self, file_coverages: List[FileCoverage], overall_coverage: float) -> Dict[str, bool]:
        """检查质量门禁"""
        gates = {}
        
        # 检查整体行覆盖率
        gates['minimum_line_coverage'] = overall_coverage >= self.quality_gates['minimum_line_coverage']
        
        # 检查分支覆盖率
        if file_coverages:
            total_branches = sum(fc.branches_total for fc in file_coverages)
            covered_branches = sum(fc.branches_covered for fc in file_coverages)
            branch_coverage = (covered_branches / total_branches * 100) if total_branches > 0 else 100
            gates['minimum_branch_coverage'] = branch_coverage >= self.quality_gates['minimum_branch_coverage']
        else:
            gates['minimum_branch_coverage'] = True
        
        # 检查函数覆盖率
        if file_coverages:
            total_functions = sum(len(fc.functions) for fc in file_coverages)
            covered_functions = sum(len(fc.functions_covered) for fc in file_coverages)
            function_coverage = (covered_functions / total_functions * 100) if total_functions > 0 else 100
            gates['minimum_function_coverage'] = function_coverage >= self.quality_gates['minimum_function_coverage']
        else:
            gates['minimum_function_coverage'] = True
        
        # 检查复杂度
        high_complexity_files = [fc for fc in file_coverages if fc.complexity_score > self.quality_gates['maximum_complexity']]
        gates['maximum_complexity'] = len(high_complexity_files) == 0
        
        # 检查关键文件覆盖率
        critical_files = [
            fc for fc in file_coverages 
            if any(Path(fc.file_path).match(pattern) for pattern in self.critical_file_patterns)
        ]
        
        if critical_files:
            critical_coverage = sum(fc.line_coverage_percent for fc in critical_files) / len(critical_files)
            gates['critical_files_coverage'] = critical_coverage >= self.quality_gates['critical_files_coverage']
        else:
            gates['critical_files_coverage'] = True
        
        return gates
    
    def _generate_recommendations(self, file_coverages: List[FileCoverage], 
                                hotspots: List[CoverageHotspot], 
                                quality_gates: Dict[str, bool]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于质量门禁的建议
        if not quality_gates.get('minimum_line_coverage', True):
            recommendations.append("📊 整体行覆盖率未达标，建议优先为核心功能添加测试用例")
        
        if not quality_gates.get('minimum_branch_coverage', True):
            recommendations.append("🔀 分支覆盖率不足，建议增加条件分支的测试用例")
        
        if not quality_gates.get('minimum_function_coverage', True):
            recommendations.append("🔧 函数覆盖率不足，建议为未测试的函数添加测试用例")
        
        if not quality_gates.get('maximum_complexity', True):
            recommendations.append("🔄 存在高复杂度代码，建议重构以降低复杂度")
        
        if not quality_gates.get('critical_files_coverage', True):
            recommendations.append("⚠️ 关键文件覆盖率不足，建议优先提升核心模块的测试覆盖率")
        
        # 基于热点的建议
        high_severity_hotspots = [h for h in hotspots if h.severity == 'high']
        if high_severity_hotspots:
            recommendations.append(f"🔥 发现{len(high_severity_hotspots)}个高优先级覆盖率问题，建议优先处理")
        
        # 基于文件分析的建议
        low_coverage_files = [fc for fc in file_coverages if fc.line_coverage_percent < 50]
        if low_coverage_files:
            recommendations.append(f"📁 {len(low_coverage_files)}个文件覆盖率过低，建议重点关注")
        
        # 积极建议
        if all(quality_gates.values()):
            recommendations.append("✅ 所有质量门禁都已通过，测试覆盖率良好！")
            recommendations.append("🚀 可以考虑增加集成测试和端到端测试")
        
        return recommendations
    
    async def _get_coverage_trends(self) -> Dict[str, float]:
        """获取覆盖率趋势"""
        trends = {
            'line_coverage_change': 0.0,
            'branch_coverage_change': 0.0,
            'function_coverage_change': 0.0
        }
        
        try:
            # 这里可以实现从历史数据中获取趋势
            # 目前返回默认值
            pass
        except Exception as e:
            logger.debug(f"获取覆盖率趋势失败: {e}")
        
        return trends
    
    async def _save_analysis(self, analysis: CoverageAnalysis):
        """保存分析结果"""
        try:
            timestamp = analysis.timestamp.strftime('%Y%m%d_%H%M%S')
            analysis_file = self.reports_dir / f"coverage_analysis_{timestamp}.json"
            
            # 转换为可序列化的格式
            analysis_dict = asdict(analysis)
            analysis_dict['timestamp'] = analysis.timestamp.isoformat()
            
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"覆盖率分析结果已保存: {analysis_file}")
            
        except Exception as e:
            logger.error(f"保存覆盖率分析失败: {e}")
    
    async def generate_coverage_badge(self, coverage_percent: float) -> str:
        """生成覆盖率徽章"""
        try:
            # 确定颜色
            if coverage_percent >= 90:
                color = 'brightgreen'
            elif coverage_percent >= 80:
                color = 'green'
            elif coverage_percent >= 70:
                color = 'yellow'
            elif coverage_percent >= 60:
                color = 'orange'
            else:
                color = 'red'
            
            # 生成徽章URL
            badge_url = f"https://img.shields.io/badge/coverage-{coverage_percent:.1f}%25-{color}"
            
            # 生成Markdown
            badge_markdown = f"![Coverage]({badge_url})"
            
            # 保存徽章信息
            badge_file = self.reports_dir / "coverage_badge.md"
            with open(badge_file, 'w', encoding='utf-8') as f:
                f.write(f"# 代码覆盖率\n\n{badge_markdown}\n\n覆盖率: {coverage_percent:.1f}%\n")
            
            return badge_markdown
            
        except Exception as e:
            logger.error(f"生成覆盖率徽章失败: {e}")
            return ""
    
    async def run_coverage_with_tests(self, test_command: str = None) -> CoverageAnalysis:
        """运行测试并分析覆盖率"""
        logger.info("运行测试并分析覆盖率...")
        
        try:
            # 默认测试命令
            if not test_command:
                test_command = [
                    sys.executable, '-m', 'pytest',
                    '--cov=src',
                    '--cov-report=json:test_reports/coverage.json',
                    '--cov-report=html:test_reports/coverage_html',
                    '--cov-report=xml:test_reports/coverage.xml',
                    'tests/'
                ]
            else:
                test_command = test_command.split()
            
            # 运行测试
            result = subprocess.run(
                test_command,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning(f"测试执行有问题，返回码: {result.returncode}")
                logger.warning(f"错误输出: {result.stderr}")
            
            # 分析覆盖率
            analysis = await self.analyze_coverage()
            
            # 生成徽章
            badge = await self.generate_coverage_badge(analysis.overall_coverage)
            
            logger.info(f"测试和覆盖率分析完成，整体覆盖率: {analysis.overall_coverage:.1f}%")
            return analysis
            
        except Exception as e:
            logger.error(f"运行测试和覆盖率分析失败: {e}")
            raise


# 全局分析器实例
coverage_analyzer = CoverageAnalyzer()