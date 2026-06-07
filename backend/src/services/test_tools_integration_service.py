"""
测试工具集成服务
"""
import asyncio
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.redis_client import RedisClient
from ..utils.file_storage_utils import FileStorageUtils
from .notification_service import NotificationService
from ..core.exceptions import ValidationError, ExecutionError, ConfigurationError


class TestToolsIntegrationService:
    """测试工具集成服务"""
    
    def __init__(
        self,
        db: AsyncSession,
        redis_client: RedisClient,
        file_storage: FileStorageUtils,
        notification_service: NotificationService
    ):
        self.db = db
        self.redis = redis_client
        self.file_storage = file_storage
        self.notification_service = notification_service
        
        # 工具配置
        self.tool_configs = {
            "jmeter": {
                "executable": "jmeter",
                "supported_formats": [".jmx"],
                "result_formats": [".jtl", ".xml"]
            },
            "owasp_zap": {
                "executable": "zap-cli",
                "supported_formats": [".json", ".xml"],
                "result_formats": [".json", ".xml", ".html"]
            },
            "allure": {
                "executable": "allure",
                "supported_formats": [".json", ".xml"],
                "result_formats": [".json", ".html"]
            },
            "playwright": {
                "executable": "playwright",
                "supported_formats": [".js", ".ts", ".py"],
                "result_formats": [".json", ".xml", ".html"]
            },
            "selenium": {
                "executable": "selenium-side-runner",
                "supported_formats": [".side"],
                "result_formats": [".json", ".xml"]
            }
        }
    
    # JMeter集成
    async def run_jmeter_test(
        self,
        test_plan_path: str,
        test_config: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行JMeter性能测试"""
        try:
            # 1. 验证测试计划文件
            if not Path(test_plan_path).exists():
                raise ValidationError(f"JMeter测试计划文件不存在: {test_plan_path}")
            
            # 2. 准备执行参数
            jmeter_args = [
                "jmeter",
                "-n",  # 非GUI模式
                "-t", test_plan_path,  # 测试计划文件
            ]
            
            # 3. 配置结果文件
            result_file = tempfile.NamedTemporaryFile(suffix=".jtl", delete=False)
            jmeter_args.extend(["-l", result_file.name])
            
            # 4. 配置报告目录
            report_dir = tempfile.mkdtemp(prefix="jmeter_report_")
            jmeter_args.extend(["-e", "-o", report_dir])
            
            # 5. 添加自定义参数
            if test_config.get("thread_count"):
                jmeter_args.extend(["-Jthreads", str(test_config["thread_count"])])
            
            if test_config.get("ramp_time"):
                jmeter_args.extend(["-Jramp_time", str(test_config["ramp_time"])])
            
            if test_config.get("duration"):
                jmeter_args.extend(["-Jduration", str(test_config["duration"])])
            
            # 6. 添加系统属性
            for key, value in test_config.get("properties", {}).items():
                jmeter_args.extend([f"-J{key}", str(value)])
            
            # 7. 执行JMeter测试
            start_time = datetime.utcnow()
            
            process = await asyncio.create_subprocess_exec(
                *jmeter_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(test_plan_path).parent
            )
            
            stdout, stderr = await process.communicate()
            end_time = datetime.utcnow()
            
            # 8. 解析执行结果
            if process.returncode == 0:
                # 解析JTL结果文件
                test_results = await self._parse_jmeter_results(result_file.name)
                
                # 保存报告文件
                report_path = await self._save_jmeter_report(report_dir, execution_id)
                
                return {
                    "success": True,
                    "execution_time": (end_time - start_time).total_seconds(),
                    "results": test_results,
                    "report_path": report_path,
                    "stdout": stdout.decode("utf-8"),
                    "stderr": stderr.decode("utf-8")
                }
            else:
                return {
                    "success": False,
                    "error": stderr.decode("utf-8"),
                    "stdout": stdout.decode("utf-8"),
                    "return_code": process.returncode
                }
                
        except Exception as e:
            raise ExecutionError(f"JMeter测试执行失败: {str(e)}")
        
        finally:
            # 清理临时文件
            try:
                if 'result_file' in locals():
                    Path(result_file.name).unlink(missing_ok=True)
                if 'report_dir' in locals():
                    import shutil
                    shutil.rmtree(report_dir, ignore_errors=True)
            except:
                pass
    
    async def create_jmeter_test_plan(
        self,
        test_config: Dict[str, Any]
    ) -> str:
        """创建JMeter测试计划"""
        # 1. 基础测试计划模板
        test_plan_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.4.1">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="API Performance Test" enabled="true">
      <stringProp name="TestPlan.comments">Generated by Test Manager</stringProp>
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.tearDown_on_shutdown">true</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
      <elementProp name="TestPlan.arguments" elementType="Arguments" guiclass="ArgumentsPanel" testclass="Arguments" testname="User Defined Variables" enabled="true">
        <collectionProp name="Arguments.arguments"/>
      </elementProp>
      <stringProp name="TestPlan.user_define_classpath"></stringProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group" enabled="true">
        <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
        <elementProp name="ThreadGroup.main_controller" elementType="LoopController" guiclass="LoopControllerGui" testclass="LoopController" testname="Loop Controller" enabled="true">
          <boolProp name="LoopController.continue_forever">false</boolProp>
          <stringProp name="LoopController.loops">{test_config.get('loop_count', 1)}</stringProp>
        </elementProp>
        <stringProp name="ThreadGroup.num_threads">{test_config.get('thread_count', 10)}</stringProp>
        <stringProp name="ThreadGroup.ramp_time">{test_config.get('ramp_time', 60)}</stringProp>
        <boolProp name="ThreadGroup.scheduler">false</boolProp>
        <stringProp name="ThreadGroup.duration"></stringProp>
        <stringProp name="ThreadGroup.delay"></stringProp>
        <boolProp name="ThreadGroup.same_user_on_next_iteration">true</boolProp>
      </ThreadGroup>
      <hashTree>
"""
        
        # 2. 添加HTTP请求
        for i, request in enumerate(test_config.get("requests", [])):
            test_plan_xml += self._generate_http_request_xml(request, i)
        
        # 3. 添加监听器
        test_plan_xml += """
        <ResultCollector guiclass="ViewResultsFullVisualizer" testclass="ResultCollector" testname="View Results Tree" enabled="true">
          <boolProp name="ResultCollector.error_logging">false</boolProp>
          <objProp>
            <name>saveConfig</name>
            <value class="SampleSaveConfiguration">
              <time>true</time>
              <latency>true</latency>
              <timestamp>true</timestamp>
              <success>true</success>
              <label>true</label>
              <code>true</code>
              <message>true</message>
              <threadName>true</threadName>
              <dataType>true</dataType>
              <encoding>false</encoding>
              <assertions>true</assertions>
              <subresults>true</subresults>
              <responseData>false</responseData>
              <samplerData>false</samplerData>
              <xml>false</xml>
              <fieldNames>true</fieldNames>
              <responseHeaders>false</responseHeaders>
              <requestHeaders>false</requestHeaders>
              <responseDataOnError>false</responseDataOnError>
              <saveAssertionResultsFailureMessage>true</saveAssertionResultsFailureMessage>
              <assertionsResultsToSave>0</assertionsResultsToSave>
              <bytes>true</bytes>
              <sentBytes>true</sentBytes>
              <url>true</url>
              <threadCounts>true</threadCounts>
              <idleTime>true</idleTime>
              <connectTime>true</connectTime>
            </value>
          </objProp>
          <stringProp name="filename"></stringProp>
        </ResultCollector>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>"""
        
        # 4. 保存测试计划文件
        filename = f"test_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jmx"
        file_path = await self.file_storage.save_file(
            test_plan_xml.encode("utf-8"),
            "jmeter_plans",
            filename
        )
        
        return file_path
    
    # OWASP ZAP集成
    async def run_security_scan(
        self,
        target_url: str,
        scan_config: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行OWASP ZAP安全扫描"""
        try:
            # 1. 启动ZAP代理
            zap_port = scan_config.get("zap_port", 8080)
            
            # 2. 配置扫描参数
            scan_args = [
                "zap-cli",
                "--port", str(zap_port),
                "quick-scan",
                "--self-contained",
                "--start-options", "-config api.disablekey=true"
            ]
            
            # 3. 添加扫描选项
            if scan_config.get("spider_enabled", True):
                scan_args.append("--spider")
            
            if scan_config.get("ajax_spider_enabled", False):
                scan_args.append("--ajax-spider")
            
            if scan_config.get("active_scan_enabled", True):
                scan_args.append("--scanners")
                scan_args.append("all")
            
            # 4. 添加目标URL
            scan_args.append(target_url)
            
            # 5. 执行安全扫描
            start_time = datetime.utcnow()
            
            process = await asyncio.create_subprocess_exec(
                *scan_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            end_time = datetime.utcnow()
            
            # 6. 获取扫描结果
            if process.returncode == 0:
                # 导出扫描报告
                report_data = await self._export_zap_report(zap_port, execution_id)
                
                return {
                    "success": True,
                    "execution_time": (end_time - start_time).total_seconds(),
                    "target_url": target_url,
                    "report_data": report_data,
                    "stdout": stdout.decode("utf-8"),
                    "stderr": stderr.decode("utf-8")
                }
            else:
                return {
                    "success": False,
                    "error": stderr.decode("utf-8"),
                    "stdout": stdout.decode("utf-8"),
                    "return_code": process.returncode
                }
                
        except Exception as e:
            raise ExecutionError(f"安全扫描执行失败: {str(e)}")
    
    # Allure报告集成
    async def generate_allure_report(
        self,
        results_dir: str,
        report_config: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成Allure测试报告"""
        try:
            # 1. 验证结果目录
            if not Path(results_dir).exists():
                raise ValidationError(f"Allure结果目录不存在: {results_dir}")
            
            # 2. 创建报告目录
            report_dir = tempfile.mkdtemp(prefix="allure_report_")
            
            # 3. 生成报告
            allure_args = [
                "allure", "generate",
                results_dir,
                "-o", report_dir,
                "--clean"
            ]
            
            # 4. 执行Allure命令
            process = await asyncio.create_subprocess_exec(
                *allure_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # 5. 处理结果
            if process.returncode == 0:
                # 保存报告
                report_path = await self._save_allure_report(report_dir, execution_id)
                
                # 解析报告数据
                report_data = await self._parse_allure_report(report_dir)
                
                return {
                    "success": True,
                    "report_path": report_path,
                    "report_data": report_data,
                    "stdout": stdout.decode("utf-8")
                }
            else:
                return {
                    "success": False,
                    "error": stderr.decode("utf-8"),
                    "stdout": stdout.decode("utf-8"),
                    "return_code": process.returncode
                }
                
        except Exception as e:
            raise ExecutionError(f"Allure报告生成失败: {str(e)}")
        
        finally:
            # 清理临时目录
            try:
                if 'report_dir' in locals():
                    import shutil
                    shutil.rmtree(report_dir, ignore_errors=True)
            except:
                pass
    
    async def create_allure_results(
        self,
        test_results: List[Dict[str, Any]],
        results_dir: str
    ) -> bool:
        """创建Allure结果文件"""
        try:
            # 1. 确保结果目录存在
            Path(results_dir).mkdir(parents=True, exist_ok=True)
            
            # 2. 为每个测试结果创建JSON文件
            for i, result in enumerate(test_results):
                result_data = {
                    "uuid": result.get("uuid", f"test-{i}"),
                    "name": result.get("name", f"Test {i+1}"),
                    "fullName": result.get("full_name", result.get("name", f"Test {i+1}")),
                    "status": result.get("status", "unknown").lower(),
                    "start": int(datetime.fromisoformat(result.get("start_time", datetime.utcnow().isoformat())).timestamp() * 1000),
                    "stop": int(datetime.fromisoformat(result.get("end_time", datetime.utcnow().isoformat())).timestamp() * 1000),
                    "labels": [
                        {"name": "suite", "value": result.get("suite", "Default Suite")},
                        {"name": "testClass", "value": result.get("test_class", "DefaultTest")},
                        {"name": "testMethod", "value": result.get("test_method", f"test_{i}")},
                        {"name": "severity", "value": result.get("severity", "normal")},
                        {"name": "priority", "value": result.get("priority", "medium")}
                    ],
                    "parameters": result.get("parameters", []),
                    "steps": result.get("steps", []),
                    "attachments": result.get("attachments", [])
                }
                
                # 添加失败信息
                if result.get("status") == "failed" and result.get("error"):
                    result_data["statusDetails"] = {
                        "message": result.get("error_message", "Test failed"),
                        "trace": result.get("error_trace", "")
                    }
                
                # 保存结果文件
                result_filename = f"{result_data['uuid']}-result.json"
                result_path = Path(results_dir) / result_filename
                
                with open(result_path, "w", encoding="utf-8") as f:
                    json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            raise ExecutionError(f"创建Allure结果文件失败: {str(e)}")
    
    # 自定义工具集成
    async def register_custom_tool(
        self,
        tool_name: str,
        tool_config: Dict[str, Any]
    ) -> bool:
        """注册自定义测试工具"""
        # 1. 验证工具配置
        required_fields = ["executable", "supported_formats", "result_formats"]
        for field in required_fields:
            if field not in tool_config:
                raise ValidationError(f"工具配置缺少必需字段: {field}")
        
        # 2. 验证可执行文件
        executable = tool_config["executable"]
        if not await self._check_executable_exists(executable):
            raise ConfigurationError(f"可执行文件不存在: {executable}")
        
        # 3. 保存工具配置
        self.tool_configs[tool_name] = tool_config
        
        # 4. 缓存配置
        await self.redis.hset(
            "custom_tools",
            tool_name,
            json.dumps(tool_config)
        )
        
        return True
    
    async def run_custom_tool(
        self,
        tool_name: str,
        command_args: List[str],
        execution_config: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """运行自定义测试工具"""
        try:
            # 1. 获取工具配置
            if tool_name not in self.tool_configs:
                # 尝试从缓存加载
                cached_config = await self.redis.hget("custom_tools", tool_name)
                if cached_config:
                    self.tool_configs[tool_name] = json.loads(cached_config)
                else:
                    raise ValidationError(f"未知的测试工具: {tool_name}")
            
            tool_config = self.tool_configs[tool_name]
            
            # 2. 构建执行命令
            cmd = [tool_config["executable"]] + command_args
            
            # 3. 设置执行环境
            env = execution_config.get("environment", {})
            cwd = execution_config.get("working_directory")
            timeout = execution_config.get("timeout", 300)
            
            # 4. 执行工具
            start_time = datetime.utcnow()
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env if env else None,
                cwd=cwd
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise ExecutionError(f"工具执行超时: {timeout}秒")
            
            end_time = datetime.utcnow()
            
            # 5. 处理结果
            result = {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "execution_time": (end_time - start_time).total_seconds(),
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
                "tool_name": tool_name,
                "command": " ".join(cmd)
            }
            
            # 6. 解析工具特定的结果
            if hasattr(self, f"_parse_{tool_name}_results"):
                parser_method = getattr(self, f"_parse_{tool_name}_results")
                result["parsed_results"] = await parser_method(stdout, stderr)
            
            return result
            
        except Exception as e:
            raise ExecutionError(f"自定义工具执行失败: {str(e)}")
    
    # 工具管理
    async def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取可用的测试工具"""
        available_tools = {}
        
        # 检查内置工具
        for tool_name, config in self.tool_configs.items():
            if await self._check_executable_exists(config["executable"]):
                available_tools[tool_name] = {
                    **config,
                    "status": "available",
                    "version": await self._get_tool_version(tool_name, config["executable"])
                }
            else:
                available_tools[tool_name] = {
                    **config,
                    "status": "not_installed",
                    "version": None
                }
        
        # 检查自定义工具
        custom_tools = await self.redis.hgetall("custom_tools")
        for tool_name, config_str in custom_tools.items():
            if isinstance(config_str, bytes):
                config_str = config_str.decode()
            
            try:
                config = json.loads(config_str)
                if await self._check_executable_exists(config["executable"]):
                    available_tools[tool_name] = {
                        **config,
                        "status": "available",
                        "custom": True,
                        "version": await self._get_tool_version(tool_name, config["executable"])
                    }
                else:
                    available_tools[tool_name] = {
                        **config,
                        "status": "not_installed",
                        "custom": True,
                        "version": None
                    }
            except json.JSONDecodeError:
                continue
        
        return available_tools
    
    async def validate_tool_configuration(
        self,
        tool_name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证工具配置"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 1. 检查必需字段
        required_fields = ["executable", "supported_formats", "result_formats"]
        for field in required_fields:
            if field not in config:
                validation_result["valid"] = False
                validation_result["errors"].append(f"缺少必需字段: {field}")
        
        # 2. 检查可执行文件
        if "executable" in config:
            if not await self._check_executable_exists(config["executable"]):
                validation_result["valid"] = False
                validation_result["errors"].append(f"可执行文件不存在: {config['executable']}")
        
        # 3. 检查格式支持
        if "supported_formats" in config:
            if not isinstance(config["supported_formats"], list):
                validation_result["valid"] = False
                validation_result["errors"].append("supported_formats必须是列表")
        
        if "result_formats" in config:
            if not isinstance(config["result_formats"], list):
                validation_result["valid"] = False
                validation_result["errors"].append("result_formats必须是列表")
        
        return validation_result
    
    # 私有方法
    async def _parse_jmeter_results(self, jtl_file: str) -> Dict[str, Any]:
        """解析JMeter结果文件"""
        try:
            results = {
                "total_samples": 0,
                "success_samples": 0,
                "error_samples": 0,
                "avg_response_time": 0,
                "min_response_time": float('inf'),
                "max_response_time": 0,
                "throughput": 0,
                "error_rate": 0,
                "samples": []
            }
            
            with open(jtl_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                if not lines:
                    return results
                
                # 跳过标题行
                data_lines = lines[1:] if lines[0].startswith('timeStamp') else lines
                
                total_time = 0
                for line in data_lines:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        try:
                            timestamp = int(parts[0])
                            elapsed = int(parts[1])
                            success = parts[2].lower() == 'true'
                            
                            results["total_samples"] += 1
                            if success:
                                results["success_samples"] += 1
                            else:
                                results["error_samples"] += 1
                            
                            total_time += elapsed
                            results["min_response_time"] = min(results["min_response_time"], elapsed)
                            results["max_response_time"] = max(results["max_response_time"], elapsed)
                            
                            results["samples"].append({
                                "timestamp": timestamp,
                                "elapsed": elapsed,
                                "success": success,
                                "label": parts[3] if len(parts) > 3 else "Unknown"
                            })
                            
                        except (ValueError, IndexError):
                            continue
                
                # 计算统计信息
                if results["total_samples"] > 0:
                    results["avg_response_time"] = total_time / results["total_samples"]
                    results["error_rate"] = (results["error_samples"] / results["total_samples"]) * 100
                    
                    # 计算吞吐量（每秒请求数）
                    if results["samples"]:
                        duration = (results["samples"][-1]["timestamp"] - results["samples"][0]["timestamp"]) / 1000
                        if duration > 0:
                            results["throughput"] = results["total_samples"] / duration
                
                if results["min_response_time"] == float('inf'):
                    results["min_response_time"] = 0
            
            return results
            
        except Exception as e:
            return {"error": f"解析JMeter结果失败: {str(e)}"}
    
    async def _save_jmeter_report(self, report_dir: str, execution_id: Optional[str]) -> str:
        """保存JMeter报告"""
        try:
            # 压缩报告目录
            import shutil
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"jmeter_report_{execution_id or timestamp}"
            
            # 创建压缩文件
            archive_path = shutil.make_archive(
                f"/tmp/{archive_name}",
                'zip',
                report_dir
            )
            
            # 保存到文件存储
            with open(archive_path, 'rb') as f:
                file_path = await self.file_storage.save_file(
                    f.read(),
                    "jmeter_reports",
                    f"{archive_name}.zip"
                )
            
            # 清理临时文件
            Path(archive_path).unlink(missing_ok=True)
            
            return file_path
            
        except Exception as e:
            raise ExecutionError(f"保存JMeter报告失败: {str(e)}")
    
    async def _export_zap_report(self, zap_port: int, execution_id: Optional[str]) -> Dict[str, Any]:
        """导出ZAP扫描报告"""
        try:
            # 使用ZAP API导出报告
            import aiohttp
            
            base_url = f"http://localhost:{zap_port}"
            
            async with aiohttp.ClientSession() as session:
                # 获取扫描结果
                async with session.get(f"{base_url}/JSON/core/view/alerts/") as response:
                    if response.status == 200:
                        alerts_data = await response.json()
                        
                        # 处理告警数据
                        processed_alerts = []
                        for alert in alerts_data.get("alerts", []):
                            processed_alerts.append({
                                "name": alert.get("name", "Unknown"),
                                "risk": alert.get("risk", "Unknown"),
                                "confidence": alert.get("confidence", "Unknown"),
                                "description": alert.get("description", ""),
                                "solution": alert.get("solution", ""),
                                "instances": len(alert.get("instances", []))
                            })
                        
                        # 生成报告摘要
                        risk_summary = {}
                        for alert in processed_alerts:
                            risk = alert["risk"]
                            risk_summary[risk] = risk_summary.get(risk, 0) + 1
                        
                        return {
                            "total_alerts": len(processed_alerts),
                            "risk_summary": risk_summary,
                            "alerts": processed_alerts,
                            "scan_timestamp": datetime.utcnow().isoformat()
                        }
                    else:
                        return {"error": f"无法获取ZAP扫描结果: HTTP {response.status}"}
                        
        except Exception as e:
            return {"error": f"导出ZAP报告失败: {str(e)}"}
    
    async def _save_allure_report(self, report_dir: str, execution_id: Optional[str]) -> str:
        """保存Allure报告"""
        try:
            import shutil
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"allure_report_{execution_id or timestamp}"
            
            # 创建压缩文件
            archive_path = shutil.make_archive(
                f"/tmp/{archive_name}",
                'zip',
                report_dir
            )
            
            # 保存到文件存储
            with open(archive_path, 'rb') as f:
                file_path = await self.file_storage.save_file(
                    f.read(),
                    "allure_reports",
                    f"{archive_name}.zip"
                )
            
            # 清理临时文件
            Path(archive_path).unlink(missing_ok=True)
            
            return file_path
            
        except Exception as e:
            raise ExecutionError(f"保存Allure报告失败: {str(e)}")
    
    async def _parse_allure_report(self, report_dir: str) -> Dict[str, Any]:
        """解析Allure报告数据"""
        try:
            # 读取widgets数据
            widgets_dir = Path(report_dir) / "widgets"
            
            report_data = {
                "summary": {},
                "suites": {},
                "categories": {},
                "timeline": {}
            }
            
            # 解析summary.json
            summary_file = widgets_dir / "summary.json"
            if summary_file.exists():
                with open(summary_file, 'r', encoding='utf-8') as f:
                    report_data["summary"] = json.load(f)
            
            # 解析suites.json
            suites_file = widgets_dir / "suites.json"
            if suites_file.exists():
                with open(suites_file, 'r', encoding='utf-8') as f:
                    report_data["suites"] = json.load(f)
            
            # 解析categories.json
            categories_file = widgets_dir / "categories.json"
            if categories_file.exists():
                with open(categories_file, 'r', encoding='utf-8') as f:
                    report_data["categories"] = json.load(f)
            
            return report_data
            
        except Exception as e:
            return {"error": f"解析Allure报告失败: {str(e)}"}
    
    def _generate_http_request_xml(self, request: Dict[str, Any], index: int) -> str:
        """生成HTTP请求的XML配置"""
        method = request.get("method", "GET").upper()
        url = request.get("url", "")
        headers = request.get("headers", {})
        body = request.get("body", "")
        
        # 解析URL
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        
        xml = f"""
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="HTTP Request {index + 1}" enabled="true">
          <elementProp name="HTTPsampler.Arguments" elementType="Arguments" guiclass="HTTPArgumentsPanel" testclass="Arguments" testname="User Defined Variables" enabled="true">
            <collectionProp name="Arguments.arguments"/>
          </elementProp>
          <stringProp name="HTTPSampler.domain">{parsed_url.hostname or ""}</stringProp>
          <stringProp name="HTTPSampler.port">{parsed_url.port or ""}</stringProp>
          <stringProp name="HTTPSampler.protocol">{parsed_url.scheme or "http"}</stringProp>
          <stringProp name="HTTPSampler.contentEncoding"></stringProp>
          <stringProp name="HTTPSampler.path">{parsed_url.path or "/"}</stringProp>
          <stringProp name="HTTPSampler.method">{method}</stringProp>
          <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
          <boolProp name="HTTPSampler.auto_redirects">false</boolProp>
          <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
          <boolProp name="HTTPSampler.DO_MULTIPART_POST">false</boolProp>
          <stringProp name="HTTPSampler.embedded_url_re"></stringProp>
          <stringProp name="HTTPSampler.connect_timeout"></stringProp>
          <stringProp name="HTTPSampler.response_timeout"></stringProp>
        </HTTPSamplerProxy>
        <hashTree>"""
        
        # 添加请求头
        if headers:
            xml += """
          <HeaderManager guiclass="HeaderPanel" testclass="HeaderManager" testname="HTTP Header Manager" enabled="true">
            <collectionProp name="HeaderManager.headers">"""
            
            for name, value in headers.items():
                xml += f"""
              <elementProp name="" elementType="Header">
                <stringProp name="Header.name">{name}</stringProp>
                <stringProp name="Header.value">{value}</stringProp>
              </elementProp>"""
            
            xml += """
            </collectionProp>
          </HeaderManager>
          <hashTree/>"""
        
        xml += """
        </hashTree>"""
        
        return xml
    
    async def _check_executable_exists(self, executable: str) -> bool:
        """检查可执行文件是否存在"""
        try:
            process = await asyncio.create_subprocess_exec(
                "which" if os.name != 'nt' else "where",
                executable,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except Exception:
            return False
    
    async def _get_tool_version(self, tool_name: str, executable: str) -> Optional[str]:
        """获取工具版本"""
        try:
            # 常见的版本命令
            version_args = ["--version", "-version", "-v", "version"]
            
            for arg in version_args:
                try:
                    process = await asyncio.create_subprocess_exec(
                        executable, arg,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        output = stdout.decode("utf-8").strip()
                        if output:
                            # 提取版本号（简单的正则匹配）
                            import re
                            version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', output)
                            if version_match:
                                return version_match.group(1)
                            return output.split('\n')[0][:50]  # 返回第一行的前50个字符
                            
                except Exception:
                    continue
            
            return None
            
        except Exception:
            return None