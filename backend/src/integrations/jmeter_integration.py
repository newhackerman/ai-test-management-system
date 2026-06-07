"""
JMeter集成模块
实现性能测试计划的执行，支持负载模型和监控配置
"""

import asyncio
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import csv
import re

# 模拟依赖模块
class MockLogger:
    def info(self, msg): print(f"INFO: {msg}")
    def debug(self, msg): print(f"DEBUG: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")

def get_logger(name):
    return MockLogger()

class TestExecutionError(Exception):
    pass

class ConfigurationError(Exception):
    pass

logger = get_logger(__name__)


class LoadPattern(Enum):
    """负载模式"""
    CONSTANT = "constant"  # 恒定负载
    RAMP_UP = "ramp_up"   # 递增负载
    SPIKE = "spike"       # 峰值负载
    STEP = "step"         # 阶梯负载


class TestType(Enum):
    """测试类型"""
    LOAD = "load"         # 负载测试
    STRESS = "stress"     # 压力测试
    VOLUME = "volume"     # 容量测试
    ENDURANCE = "endurance"  # 稳定性测试


@dataclass
class JMeterConfig:
    """JMeter配置"""
    jmeter_home: Optional[str] = None  # JMeter安装路径
    java_home: Optional[str] = None    # Java安装路径
    heap_size: str = "1g"              # JVM堆内存大小
    max_heap_size: str = "2g"          # JVM最大堆内存
    thread_count: int = 10             # 线程数
    ramp_up_period: int = 60           # 启动时间(秒)
    duration: int = 300                # 测试持续时间(秒)
    iterations: Optional[int] = None   # 迭代次数
    delay_between_requests: int = 0    # 请求间延迟(毫秒)
    timeout: int = 30000              # 请求超时(毫秒)
    follow_redirects: bool = True      # 跟随重定向
    use_keepalive: bool = True         # 使用Keep-Alive
    generate_report: bool = True       # 生成HTML报告
    save_response_data: bool = False   # 保存响应数据
    assertion_enabled: bool = True     # 启用断言


@dataclass
class HttpRequest:
    """HTTP请求配置"""
    name: str
    method: str = "GET"
    protocol: str = "http"
    server: str = "localhost"
    port: int = 80
    path: str = "/"
    parameters: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    content_type: Optional[str] = None
    assertions: Optional[List[Dict[str, Any]]] = None


@dataclass
class LoadModel:
    """负载模型"""
    pattern: LoadPattern
    thread_count: int
    ramp_up_period: int
    duration: int
    iterations: Optional[int] = None
    hold_load_for: Optional[int] = None  # 保持负载时间
    step_count: Optional[int] = None     # 阶梯数量
    step_duration: Optional[int] = None  # 每阶梯持续时间


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_samples: int
    error_count: int
    error_rate: float
    average_response_time: float
    median_response_time: float
    min_response_time: float
    max_response_time: float
    percentile_90: float
    percentile_95: float
    percentile_99: float
    throughput: float  # 吞吐量 (requests/sec)
    received_kb_per_sec: float
    sent_kb_per_sec: float


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    status: str
    metrics: PerformanceMetrics
    error_details: Optional[List[Dict[str, Any]]] = None
    report_path: Optional[str] = None
    log_path: Optional[str] = None
    jtl_path: Optional[str] = None


class JMeterTestPlanBuilder:
    """JMeter测试计划构建器"""
    
    def __init__(self):
        self.test_plan = None
        self.thread_groups = []
        self.http_requests = []
        
    def create_test_plan(self, name: str, comments: str = "") -> ET.Element:
        """创建测试计划"""
        test_plan = ET.Element("TestPlan", {
            "guiclass": "TestPlanGui",
            "testclass": "TestPlan",
            "testname": name,
            "enabled": "true"
        })
        
        # 添加注释
        if comments:
            comment_element = ET.SubElement(test_plan, "stringProp", {"name": "TestPlan.comments"})
            comment_element.text = comments
        
        # 添加用户定义变量
        arguments = ET.SubElement(test_plan, "elementProp", {
            "name": "TestPlan.arguments",
            "elementType": "Arguments",
            "guiclass": "ArgumentsPanel",
            "testclass": "Arguments",
            "testname": "User Defined Variables",
            "enabled": "true"
        })
        
        collection_prop = ET.SubElement(arguments, "collectionProp", {"name": "Arguments.arguments"})
        
        self.test_plan = test_plan
        return test_plan
    
    def add_thread_group(self, load_model: LoadModel, name: str = "Thread Group") -> ET.Element:
        """添加线程组"""
        thread_group = ET.SubElement(self.test_plan, "ThreadGroup", {
            "guiclass": "ThreadGroupGui",
            "testclass": "ThreadGroup",
            "testname": name,
            "enabled": "true"
        })
        
        # 线程数
        num_threads = ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.num_threads"})
        num_threads.text = str(load_model.thread_count)
        
        # 启动时间
        ramp_time = ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.ramp_time"})
        ramp_time.text = str(load_model.ramp_up_period)
        
        # 循环控制
        if load_model.iterations:
            loops = ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.loops"})
            loops.text = str(load_model.iterations)
            same_user = ET.SubElement(thread_group, "boolProp", {"name": "ThreadGroup.same_user_on_next_iteration"})
            same_user.text = "true"
        else:
            # 持续时间控制
            scheduler = ET.SubElement(thread_group, "boolProp", {"name": "ThreadGroup.scheduler"})
            scheduler.text = "true"
            duration = ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.duration"})
            duration.text = str(load_model.duration)
            
        self.thread_groups.append(thread_group)
        return thread_group
    
    def add_http_request(self, request: HttpRequest, thread_group: ET.Element) -> ET.Element:
        """添加HTTP请求"""
        http_sampler = ET.SubElement(thread_group, "HTTPSamplerProxy", {
            "guiclass": "HttpTestSampleGui",
            "testclass": "HTTPSamplerProxy",
            "testname": request.name,
            "enabled": "true"
        })
        
        # 基本配置
        protocol = ET.SubElement(http_sampler, "stringProp", {"name": "HTTPSampler.protocol"})
        protocol.text = request.protocol
        
        domain = ET.SubElement(http_sampler, "stringProp", {"name": "HTTPSampler.domain"})
        domain.text = request.server
        
        port = ET.SubElement(http_sampler, "stringProp", {"name": "HTTPSampler.port"})
        port.text = str(request.port)
        
        path = ET.SubElement(http_sampler, "stringProp", {"name": "HTTPSampler.path"})
        path.text = request.path
        
        method = ET.SubElement(http_sampler, "stringProp", {"name": "HTTPSampler.method"})
        method.text = request.method
        
        # 请求参数
        if request.parameters:
            arguments = ET.SubElement(http_sampler, "elementProp", {
                "name": "HTTPsampler.Arguments",
                "elementType": "Arguments",
                "guiclass": "HTTPArgumentsPanel",
                "testclass": "Arguments",
                "testname": "User Defined Variables",
                "enabled": "true"
            })
            
            collection_prop = ET.SubElement(arguments, "collectionProp", {"name": "Arguments.arguments"})
            
            for key, value in request.parameters.items():
                arg = ET.SubElement(collection_prop, "elementProp", {
                    "name": key,
                    "elementType": "HTTPArgument"
                })
                
                arg_name = ET.SubElement(arg, "stringProp", {"name": "Argument.name"})
                arg_name.text = key
                
                arg_value = ET.SubElement(arg, "stringProp", {"name": "Argument.value"})
                arg_value.text = value
                
                arg_metadata = ET.SubElement(arg, "stringProp", {"name": "Argument.metadata"})
                arg_metadata.text = "="
        
        # 请求头
        if request.headers:
            header_manager = ET.SubElement(http_sampler, "HeaderManager", {
                "guiclass": "HeaderPanel",
                "testclass": "HeaderManager",
                "testname": "HTTP Header Manager",
                "enabled": "true"
            })
            
            collection_prop = ET.SubElement(header_manager, "collectionProp", {"name": "HeaderManager.headers"})
            
            for key, value in request.headers.items():
                header = ET.SubElement(collection_prop, "elementProp", {
                    "name": "",
                    "elementType": "Header"
                })
                
                header_name = ET.SubElement(header, "stringProp", {"name": "Header.name"})
                header_name.text = key
                
                header_value = ET.SubElement(header, "stringProp", {"name": "Header.value"})
                header_value.text = value
        
        # 请求体
        if request.body:
            body_data = ET.SubElement(http_sampler, "boolProp", {"name": "HTTPSampler.postBodyRaw"})
            body_data.text = "true"
            
            arguments = ET.SubElement(http_sampler, "elementProp", {
                "name": "HTTPsampler.Arguments",
                "elementType": "Arguments"
            })
            
            collection_prop = ET.SubElement(arguments, "collectionProp", {"name": "Arguments.arguments"})
            
            arg = ET.SubElement(collection_prop, "elementProp", {
                "name": "",
                "elementType": "HTTPArgument"
            })
            
            arg_value = ET.SubElement(arg, "stringProp", {"name": "Argument.value"})
            arg_value.text = request.body
        
        # 添加断言
        if request.assertions:
            for assertion in request.assertions:
                self._add_assertion(http_sampler, assertion)
        
        self.http_requests.append(http_sampler)
        return http_sampler
    
    def _add_assertion(self, parent: ET.Element, assertion: Dict[str, Any]):
        """添加断言"""
        assertion_type = assertion.get("type", "response")
        
        if assertion_type == "response":
            response_assertion = ET.SubElement(parent, "ResponseAssertion", {
                "guiclass": "AssertionGui",
                "testclass": "ResponseAssertion",
                "testname": "Response Assertion",
                "enabled": "true"
            })
            
            # 断言字段
            field = ET.SubElement(response_assertion, "stringProp", {"name": "Assertion.test_field"})
            field.text = assertion.get("field", "Assertion.response_data")
            
            # 断言模式
            patterns = ET.SubElement(response_assertion, "collectionProp", {"name": "Asserion.test_strings"})
            
            pattern = ET.SubElement(patterns, "stringProp", {"name": "0"})
            pattern.text = assertion.get("pattern", "")
            
            # 断言类型
            test_type = ET.SubElement(response_assertion, "stringProp", {"name": "Assertion.test_type"})
            test_type.text = str(assertion.get("test_type", 16))  # 16 = contains
    
    def add_listeners(self, thread_group: ET.Element, jtl_path: str):
        """添加监听器"""
        # 结果树监听器
        result_tree = ET.SubElement(thread_group, "ResultCollector", {
            "guiclass": "ViewResultsFullVisualizer",
            "testclass": "ResultCollector",
            "testname": "View Results Tree",
            "enabled": "true"
        })
        
        filename = ET.SubElement(result_tree, "stringProp", {"name": "filename"})
        filename.text = jtl_path
        
        # 聚合报告监听器
        aggregate_report = ET.SubElement(thread_group, "ResultCollector", {
            "guiclass": "StatVisualizer",
            "testclass": "ResultCollector",
            "testname": "Aggregate Report",
            "enabled": "true"
        })
    
    def save_test_plan(self, file_path: str):
        """保存测试计划"""
        if not self.test_plan:
            raise ValueError("测试计划未创建")
        
        # 创建根元素
        jmeter_test_plan = ET.Element("jmeterTestPlan", {
            "version": "1.2",
            "properties": "5.0",
            "jmeter": "5.4.1"
        })
        
        hash_tree = ET.SubElement(jmeter_test_plan, "hashTree")
        hash_tree.append(self.test_plan)
        
        # 为每个线程组添加hashTree
        for thread_group in self.thread_groups:
            thread_hash_tree = ET.SubElement(hash_tree, "hashTree")
            
            # 为线程组中的每个HTTP请求添加hashTree
            for request in thread_group.findall(".//HTTPSamplerProxy"):
                request_hash_tree = ET.SubElement(thread_hash_tree, "hashTree")
        
        # 格式化XML
        self._indent(jmeter_test_plan)
        
        # 保存文件
        tree = ET.ElementTree(jmeter_test_plan)
        tree.write(file_path, encoding="utf-8", xml_declaration=True)
        
        logger.info(f"JMeter测试计划已保存: {file_path}")
    
    def _indent(self, elem, level=0):
        """格式化XML缩进"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i


class JMeterExecutor:
    """JMeter执行器"""
    
    def __init__(self, config: JMeterConfig):
        self.config = config
        self.jmeter_path = self._find_jmeter_path()
        
    def _find_jmeter_path(self) -> str:
        """查找JMeter路径"""
        if self.config.jmeter_home:
            jmeter_path = Path(self.config.jmeter_home) / "bin" / "jmeter"
            if jmeter_path.exists():
                return str(jmeter_path)
        
        # 尝试从PATH中查找
        try:
            result = subprocess.run(["which", "jmeter"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # 尝试常见安装路径
        common_paths = [
            "/usr/local/apache-jmeter/bin/jmeter",
            "/opt/apache-jmeter/bin/jmeter",
            "C:\\apache-jmeter\\bin\\jmeter.bat"
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
        
        raise ConfigurationError("未找到JMeter安装路径，请设置JMETER_HOME环境变量或在配置中指定")
    
    async def execute_test_plan(self, jmx_path: str, test_id: str) -> TestResult:
        """执行测试计划"""
        start_time = datetime.now()
        
        # 创建输出目录
        output_dir = Path(f"jmeter_results/{test_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        jtl_path = output_dir / "results.jtl"
        log_path = output_dir / "jmeter.log"
        report_dir = output_dir / "html_report"
        
        try:
            # 构建JMeter命令
            cmd = [
                self.jmeter_path,
                "-n",  # 非GUI模式
                "-t", str(jmx_path),  # 测试计划文件
                "-l", str(jtl_path),  # 结果文件
                "-j", str(log_path),  # 日志文件
            ]
            
            # 添加JVM参数
            env = os.environ.copy()
            if self.config.java_home:
                env["JAVA_HOME"] = self.config.java_home
            
            jvm_args = f"-Xms{self.config.heap_size} -Xmx{self.config.max_heap_size}"
            env["JVM_ARGS"] = jvm_args
            
            # 生成HTML报告
            if self.config.generate_report:
                cmd.extend(["-e", "-o", str(report_dir)])
            
            logger.info(f"开始执行JMeter测试: {' '.join(cmd)}")
            
            # 执行JMeter
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            if process.returncode == 0:
                logger.info(f"JMeter测试执行成功: {test_id}")
                status = "PASSED"
            else:
                logger.error(f"JMeter测试执行失败: {test_id}, 错误: {stderr.decode()}")
                status = "FAILED"
            
            # 解析结果
            metrics = await self._parse_jtl_results(jtl_path)
            error_details = await self._parse_error_details(jtl_path)
            
            result = TestResult(
                test_id=test_id,
                test_name=Path(jmx_path).stem,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                status=status,
                metrics=metrics,
                error_details=error_details,
                report_path=str(report_dir) if self.config.generate_report else None,
                log_path=str(log_path),
                jtl_path=str(jtl_path)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"JMeter测试执行异常: {test_id}, 错误: {str(e)}")
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            return TestResult(
                test_id=test_id,
                test_name=Path(jmx_path).stem,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                status="ERROR",
                metrics=PerformanceMetrics(
                    total_samples=0, error_count=0, error_rate=0.0,
                    average_response_time=0.0, median_response_time=0.0,
                    min_response_time=0.0, max_response_time=0.0,
                    percentile_90=0.0, percentile_95=0.0, percentile_99=0.0,
                    throughput=0.0, received_kb_per_sec=0.0, sent_kb_per_sec=0.0
                ),
                error_details=[{"error": str(e)}]
            )
    
    async def _parse_jtl_results(self, jtl_path: Path) -> PerformanceMetrics:
        """解析JTL结果文件"""
        if not jtl_path.exists():
            logger.warning(f"JTL文件不存在: {jtl_path}")
            return PerformanceMetrics(
                total_samples=0, error_count=0, error_rate=0.0,
                average_response_time=0.0, median_response_time=0.0,
                min_response_time=0.0, max_response_time=0.0,
                percentile_90=0.0, percentile_95=0.0, percentile_99=0.0,
                throughput=0.0, received_kb_per_sec=0.0, sent_kb_per_sec=0.0
            )
        
        try:
            response_times = []
            error_count = 0
            total_samples = 0
            total_bytes_received = 0
            total_bytes_sent = 0
            start_time = None
            end_time = None
            
            with open(jtl_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    total_samples += 1
                    
                    # 响应时间
                    elapsed = int(row.get('elapsed', 0))
                    response_times.append(elapsed)
                    
                    # 错误统计
                    success = row.get('success', 'true').lower() == 'true'
                    if not success:
                        error_count += 1
                    
                    # 字节统计
                    bytes_received = int(row.get('bytes', 0))
                    bytes_sent = int(row.get('sentBytes', 0))
                    total_bytes_received += bytes_received
                    total_bytes_sent += bytes_sent
                    
                    # 时间范围
                    timestamp = int(row.get('timeStamp', 0))
                    if start_time is None or timestamp < start_time:
                        start_time = timestamp
                    if end_time is None or timestamp + elapsed > end_time:
                        end_time = timestamp + elapsed
            
            if not response_times:
                return PerformanceMetrics(
                    total_samples=0, error_count=0, error_rate=0.0,
                    average_response_time=0.0, median_response_time=0.0,
                    min_response_time=0.0, max_response_time=0.0,
                    percentile_90=0.0, percentile_95=0.0, percentile_99=0.0,
                    throughput=0.0, received_kb_per_sec=0.0, sent_kb_per_sec=0.0
                )
            
            # 计算统计指标
            response_times.sort()
            
            average_response_time = sum(response_times) / len(response_times)
            median_response_time = response_times[len(response_times) // 2]
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # 百分位数
            percentile_90 = response_times[int(len(response_times) * 0.9)]
            percentile_95 = response_times[int(len(response_times) * 0.95)]
            percentile_99 = response_times[int(len(response_times) * 0.99)]
            
            # 吞吐量计算
            duration_seconds = (end_time - start_time) / 1000.0 if start_time and end_time else 1
            throughput = total_samples / duration_seconds if duration_seconds > 0 else 0
            
            # 带宽计算
            received_kb_per_sec = (total_bytes_received / 1024) / duration_seconds if duration_seconds > 0 else 0
            sent_kb_per_sec = (total_bytes_sent / 1024) / duration_seconds if duration_seconds > 0 else 0
            
            error_rate = (error_count / total_samples * 100) if total_samples > 0 else 0
            
            return PerformanceMetrics(
                total_samples=total_samples,
                error_count=error_count,
                error_rate=error_rate,
                average_response_time=average_response_time,
                median_response_time=median_response_time,
                min_response_time=min_response_time,
                max_response_time=max_response_time,
                percentile_90=percentile_90,
                percentile_95=percentile_95,
                percentile_99=percentile_99,
                throughput=throughput,
                received_kb_per_sec=received_kb_per_sec,
                sent_kb_per_sec=sent_kb_per_sec
            )
            
        except Exception as e:
            logger.error(f"解析JTL文件失败: {str(e)}")
            return PerformanceMetrics(
                total_samples=0, error_count=0, error_rate=0.0,
                average_response_time=0.0, median_response_time=0.0,
                min_response_time=0.0, max_response_time=0.0,
                percentile_90=0.0, percentile_95=0.0, percentile_99=0.0,
                throughput=0.0, received_kb_per_sec=0.0, sent_kb_per_sec=0.0
            )
    
    async def _parse_error_details(self, jtl_path: Path) -> List[Dict[str, Any]]:
        """解析错误详情"""
        error_details = []
        
        if not jtl_path.exists():
            return error_details
        
        try:
            with open(jtl_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    success = row.get('success', 'true').lower() == 'true'
                    if not success:
                        error_detail = {
                            "timestamp": row.get('timeStamp'),
                            "label": row.get('label'),
                            "response_code": row.get('responseCode'),
                            "response_message": row.get('responseMessage'),
                            "failure_message": row.get('failureMessage', ''),
                            "url": row.get('URL', ''),
                            "elapsed": row.get('elapsed')
                        }
                        error_details.append(error_detail)
        
        except Exception as e:
            logger.error(f"解析错误详情失败: {str(e)}")
        
        return error_details


class JMeterIntegration:
    """JMeter集成主类"""
    
    def __init__(self):
        self.default_config = JMeterConfig()
    
    async def create_and_execute_test(
        self,
        test_name: str,
        requests: List[HttpRequest],
        load_model: LoadModel,
        config: Optional[JMeterConfig] = None
    ) -> TestResult:
        """创建并执行性能测试"""
        execution_config = config or self.default_config
        
        # 创建测试计划
        builder = JMeterTestPlanBuilder()
        test_plan = builder.create_test_plan(test_name, f"性能测试计划: {test_name}")
        
        # 添加线程组
        thread_group = builder.add_thread_group(load_model, "Main Thread Group")
        
        # 添加HTTP请求
        for request in requests:
            builder.add_http_request(request, thread_group)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jmx', delete=False) as f:
            jmx_path = f.name
        
        try:
            # 保存测试计划
            builder.save_test_plan(jmx_path)
            
            # 执行测试
            executor = JMeterExecutor(execution_config)
            result = await executor.execute_test_plan(jmx_path, test_name)
            
            return result
            
        finally:
            # 清理临时文件
            if Path(jmx_path).exists():
                Path(jmx_path).unlink()
    
    def create_load_test_config(
        self,
        thread_count: int = 10,
        ramp_up_period: int = 60,
        duration: int = 300
    ) -> LoadModel:
        """创建负载测试配置"""
        return LoadModel(
            pattern=LoadPattern.RAMP_UP,
            thread_count=thread_count,
            ramp_up_period=ramp_up_period,
            duration=duration
        )
    
    def create_stress_test_config(
        self,
        max_threads: int = 100,
        ramp_up_period: int = 300,
        hold_duration: int = 600
    ) -> LoadModel:
        """创建压力测试配置"""
        return LoadModel(
            pattern=LoadPattern.STEP,
            thread_count=max_threads,
            ramp_up_period=ramp_up_period,
            duration=hold_duration,
            step_count=5,
            step_duration=ramp_up_period // 5
        )
    
    def create_spike_test_config(
        self,
        normal_threads: int = 10,
        spike_threads: int = 100,
        spike_duration: int = 60
    ) -> LoadModel:
        """创建峰值测试配置"""
        return LoadModel(
            pattern=LoadPattern.SPIKE,
            thread_count=spike_threads,
            ramp_up_period=10,  # 快速启动
            duration=spike_duration,
            hold_load_for=spike_duration - 20  # 保持峰值负载
        )
    
    def create_sample_http_request(self) -> HttpRequest:
        """创建示例HTTP请求"""
        return HttpRequest(
            name="Sample API Request",
            method="GET",
            protocol="https",
            server="httpbin.org",
            port=443,
            path="/get",
            headers={
                "User-Agent": "JMeter Performance Test",
                "Accept": "application/json"
            },
            assertions=[
                {
                    "type": "response",
                    "field": "Assertion.response_code",
                    "pattern": "200",
                    "test_type": 1  # equals
                }
            ]
        )


# 导出主要类和函数
__all__ = [
    "JMeterIntegration",
    "JMeterConfig",
    "HttpRequest",
    "LoadModel",
    "LoadPattern",
    "TestType",
    "PerformanceMetrics",
    "TestResult"
]