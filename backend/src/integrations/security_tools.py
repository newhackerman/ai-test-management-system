"""
安全测试工具集成模块
集成OWASP ZAP、Nmap等安全工具，实现漏洞扫描和渗透测试
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
import requests
import time

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


class SeverityLevel(Enum):
    """漏洞严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScanType(Enum):
    """扫描类型"""
    PASSIVE = "passive"      # 被动扫描
    ACTIVE = "active"        # 主动扫描
    SPIDER = "spider"        # 爬虫扫描
    AJAX_SPIDER = "ajax"     # AJAX爬虫
    BASELINE = "baseline"    # 基线扫描
    FULL = "full"           # 全面扫描


class VulnerabilityType(Enum):
    """漏洞类型"""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SESSION_MANAGEMENT = "session_management"
    INPUT_VALIDATION = "input_validation"
    ERROR_HANDLING = "error_handling"
    CRYPTOGRAPHY = "cryptography"
    CONFIGURATION = "configuration"
    INFORMATION_DISCLOSURE = "information_disclosure"


@dataclass
class SecurityConfig:
    """安全测试配置"""
    zap_proxy_host: str = "127.0.0.1"
    zap_proxy_port: int = 8080
    zap_api_key: Optional[str] = None
    scan_timeout: int = 3600  # 扫描超时时间(秒)
    max_scan_depth: int = 5   # 最大扫描深度
    thread_count: int = 5     # 扫描线程数
    delay_between_requests: int = 0  # 请求间延迟(毫秒)
    user_agent: str = "Security Scanner"
    include_patterns: Optional[List[str]] = None  # 包含的URL模式
    exclude_patterns: Optional[List[str]] = None  # 排除的URL模式
    authentication_config: Optional[Dict[str, Any]] = None  # 认证配置


@dataclass
class Vulnerability:
    """漏洞信息"""
    id: str
    name: str
    description: str
    severity: SeverityLevel
    confidence: str
    vulnerability_type: VulnerabilityType
    url: str
    method: str = "GET"
    parameter: Optional[str] = None
    attack: Optional[str] = None
    evidence: Optional[str] = None
    solution: Optional[str] = None
    reference: Optional[str] = None
    cwe_id: Optional[int] = None
    wasc_id: Optional[int] = None


@dataclass
class ScanResult:
    """扫描结果"""
    scan_id: str
    target_url: str
    scan_type: ScanType
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    status: str
    vulnerabilities: List[Vulnerability]
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    urls_scanned: int
    report_path: Optional[str] = None


class ZAPIntegration:
    """OWASP ZAP集成"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.base_url = f"http://{config.zap_proxy_host}:{config.zap_proxy_port}"
        self.api_key = config.zap_api_key
        self.session = requests.Session()
        
    def _make_api_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发起ZAP API请求"""
        url = f"{self.base_url}/JSON/{endpoint}"
        
        request_params = params or {}
        if self.api_key:
            request_params["apikey"] = self.api_key
        
        try:
            response = self.session.get(url, params=request_params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"ZAP API请求失败: {url}, 错误: {str(e)}")
            raise TestExecutionError(f"ZAP API请求失败: {str(e)}")
    
    def _make_api_post(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """发起ZAP API POST请求"""
        url = f"{self.base_url}/JSON/{endpoint}"
        
        request_data = data or {}
        if self.api_key:
            request_data["apikey"] = self.api_key
        
        try:
            response = self.session.post(url, data=request_data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"ZAP API POST请求失败: {url}, 错误: {str(e)}")
            raise TestExecutionError(f"ZAP API POST请求失败: {str(e)}")
    
    async def check_zap_status(self) -> bool:
        """检查ZAP服务状态"""
        try:
            result = self._make_api_request("core/view/version")
            logger.info(f"ZAP版本: {result.get('version', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"ZAP服务不可用: {str(e)}")
            return False
    
    async def create_new_session(self, session_name: str) -> str:
        """创建新的扫描会话"""
        try:
            result = self._make_api_post("core/action/newSession", {"name": session_name})
            logger.info(f"创建ZAP会话: {session_name}")
            return session_name
        except Exception as e:
            logger.error(f"创建ZAP会话失败: {str(e)}")
            raise TestExecutionError(f"创建ZAP会话失败: {str(e)}")
    
    async def configure_authentication(self, target_url: str, auth_config: Dict[str, Any]):
        """配置认证"""
        if not auth_config:
            return
        
        auth_type = auth_config.get("type", "form")
        
        if auth_type == "form":
            # 表单认证
            login_url = auth_config.get("login_url")
            username_field = auth_config.get("username_field", "username")
            password_field = auth_config.get("password_field", "password")
            username = auth_config.get("username")
            password = auth_config.get("password")
            
            if login_url and username and password:
                # 设置认证方法
                self._make_api_post("authentication/action/setAuthenticationMethod", {
                    "contextId": "0",
                    "authMethodName": "formBasedAuthentication",
                    "authMethodConfigParams": f"loginUrl={login_url}&loginRequestData={username_field}%3D{username}%26{password_field}%3D{password}"
                })
                
                logger.info(f"配置表单认证: {login_url}")
        
        elif auth_type == "basic":
            # Basic认证
            username = auth_config.get("username")
            password = auth_config.get("password")
            
            if username and password:
                # 设置HTTP认证
                self._make_api_post("httpSessions/action/createEmptySession", {
                    "site": target_url,
                    "session": "auth_session"
                })
                
                logger.info("配置Basic认证")
    
    async def spider_scan(self, target_url: str, max_depth: Optional[int] = None) -> str:
        """执行爬虫扫描"""
        params = {"url": target_url}
        if max_depth:
            params["maxChildren"] = str(max_depth)
        
        result = self._make_api_post("spider/action/scan", params)
        scan_id = result.get("scan")
        
        logger.info(f"开始爬虫扫描: {target_url}, 扫描ID: {scan_id}")
        
        # 等待扫描完成
        while True:
            status_result = self._make_api_request("spider/view/status", {"scanId": scan_id})
            status = int(status_result.get("status", 0))
            
            if status >= 100:
                break
            
            logger.debug(f"爬虫扫描进度: {status}%")
            await asyncio.sleep(5)
        
        logger.info(f"爬虫扫描完成: {scan_id}")
        return scan_id
    
    async def ajax_spider_scan(self, target_url: str) -> str:
        """执行AJAX爬虫扫描"""
        result = self._make_api_post("ajaxSpider/action/scan", {"url": target_url})
        
        logger.info(f"开始AJAX爬虫扫描: {target_url}")
        
        # 等待扫描完成
        while True:
            status_result = self._make_api_request("ajaxSpider/view/status")
            status = status_result.get("status", "stopped")
            
            if status == "stopped":
                break
            
            logger.debug(f"AJAX爬虫扫描状态: {status}")
            await asyncio.sleep(5)
        
        logger.info("AJAX爬虫扫描完成")
        return "ajax_scan"
    
    async def active_scan(self, target_url: str, policy: Optional[str] = None) -> str:
        """执行主动扫描"""
        params = {"url": target_url}
        if policy:
            params["scanPolicyName"] = policy
        
        result = self._make_api_post("ascan/action/scan", params)
        scan_id = result.get("scan")
        
        logger.info(f"开始主动扫描: {target_url}, 扫描ID: {scan_id}")
        
        # 等待扫描完成
        start_time = time.time()
        while True:
            status_result = self._make_api_request("ascan/view/status", {"scanId": scan_id})
            status = int(status_result.get("status", 0))
            
            if status >= 100:
                break
            
            # 检查超时
            if time.time() - start_time > self.config.scan_timeout:
                logger.warning(f"主动扫描超时: {scan_id}")
                self._make_api_post("ascan/action/stop", {"scanId": scan_id})
                break
            
            logger.debug(f"主动扫描进度: {status}%")
            await asyncio.sleep(10)
        
        logger.info(f"主动扫描完成: {scan_id}")
        return scan_id
    
    async def passive_scan(self, target_url: str) -> str:
        """执行被动扫描"""
        # 被动扫描会在爬虫扫描过程中自动进行
        logger.info(f"被动扫描已启用: {target_url}")
        
        # 等待被动扫描完成
        while True:
            result = self._make_api_request("pscan/view/recordsToScan")
            records_to_scan = int(result.get("recordsToScan", 0))
            
            if records_to_scan == 0:
                break
            
            logger.debug(f"被动扫描剩余记录: {records_to_scan}")
            await asyncio.sleep(5)
        
        logger.info("被动扫描完成")
        return "passive_scan"
    
    def get_alerts(self, base_url: Optional[str] = None) -> List[Vulnerability]:
        """获取扫描发现的漏洞"""
        params = {}
        if base_url:
            params["baseurl"] = base_url
        
        result = self._make_api_request("core/view/alerts", params)
        alerts = result.get("alerts", [])
        
        vulnerabilities = []
        for alert in alerts:
            vulnerability = Vulnerability(
                id=alert.get("id", ""),
                name=alert.get("name", ""),
                description=alert.get("description", ""),
                severity=self._map_severity(alert.get("risk", "Low")),
                confidence=alert.get("confidence", ""),
                vulnerability_type=self._map_vulnerability_type(alert.get("name", "")),
                url=alert.get("url", ""),
                method=alert.get("method", "GET"),
                parameter=alert.get("param", ""),
                attack=alert.get("attack", ""),
                evidence=alert.get("evidence", ""),
                solution=alert.get("solution", ""),
                reference=alert.get("reference", ""),
                cwe_id=int(alert.get("cweid", 0)) if alert.get("cweid") else None,
                wasc_id=int(alert.get("wascid", 0)) if alert.get("wascid") else None
            )
            vulnerabilities.append(vulnerability)
        
        return vulnerabilities
    
    def _map_severity(self, risk: str) -> SeverityLevel:
        """映射严重程度"""
        risk_mapping = {
            "High": SeverityLevel.HIGH,
            "Medium": SeverityLevel.MEDIUM,
            "Low": SeverityLevel.LOW,
            "Informational": SeverityLevel.INFO
        }
        return risk_mapping.get(risk, SeverityLevel.LOW)
    
    def _map_vulnerability_type(self, name: str) -> VulnerabilityType:
        """映射漏洞类型"""
        name_lower = name.lower()
        
        if "sql" in name_lower and "injection" in name_lower:
            return VulnerabilityType.SQL_INJECTION
        elif "xss" in name_lower or "cross site scripting" in name_lower:
            return VulnerabilityType.XSS
        elif "csrf" in name_lower or "cross site request forgery" in name_lower:
            return VulnerabilityType.CSRF
        elif "authentication" in name_lower:
            return VulnerabilityType.AUTHENTICATION
        elif "authorization" in name_lower:
            return VulnerabilityType.AUTHORIZATION
        elif "session" in name_lower:
            return VulnerabilityType.SESSION_MANAGEMENT
        elif "input" in name_lower and "validation" in name_lower:
            return VulnerabilityType.INPUT_VALIDATION
        elif "error" in name_lower:
            return VulnerabilityType.ERROR_HANDLING
        elif "crypto" in name_lower or "ssl" in name_lower or "tls" in name_lower:
            return VulnerabilityType.CRYPTOGRAPHY
        elif "configuration" in name_lower or "config" in name_lower:
            return VulnerabilityType.CONFIGURATION
        elif "information" in name_lower and "disclosure" in name_lower:
            return VulnerabilityType.INFORMATION_DISCLOSURE
        else:
            return VulnerabilityType.CONFIGURATION
    
    async def generate_report(self, report_format: str = "html") -> str:
        """生成扫描报告"""
        if report_format.lower() == "html":
            result = self._make_api_request("core/other/htmlreport")
        elif report_format.lower() == "xml":
            result = self._make_api_request("core/other/xmlreport")
        elif report_format.lower() == "json":
            result = self._make_api_request("core/other/jsonreport")
        else:
            raise ValueError(f"不支持的报告格式: {report_format}")
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = Path("security_reports")
        report_dir.mkdir(exist_ok=True)
        
        report_path = report_dir / f"zap_report_{timestamp}.{report_format.lower()}"
        
        if isinstance(result, dict):
            content = json.dumps(result, indent=2, ensure_ascii=False)
        else:
            content = str(result)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"ZAP报告已生成: {report_path}")
        return str(report_path)


class NmapIntegration:
    """Nmap集成"""
    
    def __init__(self):
        self.nmap_path = self._find_nmap_path()
    
    def _find_nmap_path(self) -> str:
        """查找Nmap路径"""
        try:
            result = subprocess.run(["which", "nmap"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # 尝试常见路径
        common_paths = [
            "/usr/bin/nmap",
            "/usr/local/bin/nmap",
            "C:\\Program Files (x86)\\Nmap\\nmap.exe"
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
        
        raise ConfigurationError("未找到Nmap安装路径")
    
    async def port_scan(self, target: str, ports: str = "1-1000") -> Dict[str, Any]:
        """端口扫描"""
        cmd = [
            self.nmap_path,
            "-sS",  # SYN扫描
            "-p", ports,
            "-oX", "-",  # XML输出到stdout
            target
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return self._parse_nmap_xml(stdout.decode())
            else:
                raise TestExecutionError(f"Nmap扫描失败: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Nmap端口扫描异常: {str(e)}")
            raise TestExecutionError(f"Nmap端口扫描异常: {str(e)}")
    
    async def service_scan(self, target: str, ports: str = "1-1000") -> Dict[str, Any]:
        """服务扫描"""
        cmd = [
            self.nmap_path,
            "-sV",  # 版本检测
            "-p", ports,
            "-oX", "-",
            target
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return self._parse_nmap_xml(stdout.decode())
            else:
                raise TestExecutionError(f"Nmap服务扫描失败: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Nmap服务扫描异常: {str(e)}")
            raise TestExecutionError(f"Nmap服务扫描异常: {str(e)}")
    
    async def vulnerability_scan(self, target: str) -> Dict[str, Any]:
        """漏洞扫描"""
        cmd = [
            self.nmap_path,
            "--script", "vuln",
            "-oX", "-",
            target
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return self._parse_nmap_xml(stdout.decode())
            else:
                raise TestExecutionError(f"Nmap漏洞扫描失败: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Nmap漏洞扫描异常: {str(e)}")
            raise TestExecutionError(f"Nmap漏洞扫描异常: {str(e)}")
    
    def _parse_nmap_xml(self, xml_content: str) -> Dict[str, Any]:
        """解析Nmap XML输出"""
        try:
            root = ET.fromstring(xml_content)
            
            result = {
                "scan_info": {},
                "hosts": []
            }
            
            # 解析扫描信息
            scaninfo = root.find("scaninfo")
            if scaninfo is not None:
                result["scan_info"] = {
                    "type": scaninfo.get("type"),
                    "protocol": scaninfo.get("protocol"),
                    "numservices": scaninfo.get("numservices")
                }
            
            # 解析主机信息
            for host in root.findall("host"):
                host_info = {
                    "status": host.find("status").get("state") if host.find("status") is not None else "unknown",
                    "addresses": [],
                    "hostnames": [],
                    "ports": []
                }
                
                # 地址信息
                for address in host.findall("address"):
                    host_info["addresses"].append({
                        "addr": address.get("addr"),
                        "addrtype": address.get("addrtype")
                    })
                
                # 主机名信息
                hostnames = host.find("hostnames")
                if hostnames is not None:
                    for hostname in hostnames.findall("hostname"):
                        host_info["hostnames"].append({
                            "name": hostname.get("name"),
                            "type": hostname.get("type")
                        })
                
                # 端口信息
                ports = host.find("ports")
                if ports is not None:
                    for port in ports.findall("port"):
                        port_info = {
                            "portid": port.get("portid"),
                            "protocol": port.get("protocol"),
                            "state": port.find("state").get("state") if port.find("state") is not None else "unknown"
                        }
                        
                        # 服务信息
                        service = port.find("service")
                        if service is not None:
                            port_info["service"] = {
                                "name": service.get("name"),
                                "product": service.get("product"),
                                "version": service.get("version"),
                                "extrainfo": service.get("extrainfo")
                            }
                        
                        # 脚本输出
                        scripts = []
                        for script in port.findall("script"):
                            scripts.append({
                                "id": script.get("id"),
                                "output": script.get("output")
                            })
                        if scripts:
                            port_info["scripts"] = scripts
                        
                        host_info["ports"].append(port_info)
                
                result["hosts"].append(host_info)
            
            return result
            
        except ET.ParseError as e:
            logger.error(f"解析Nmap XML失败: {str(e)}")
            return {"error": f"XML解析失败: {str(e)}"}


class SecurityTestIntegration:
    """安全测试集成主类"""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.zap = ZAPIntegration(self.config)
        self.nmap = NmapIntegration()
    
    async def full_security_scan(self, target_url: str, scan_id: str) -> ScanResult:
        """执行完整安全扫描"""
        start_time = datetime.now()
        
        try:
            logger.info(f"开始完整安全扫描: {target_url}")
            
            # 检查ZAP状态
            if not await self.zap.check_zap_status():
                raise TestExecutionError("ZAP服务不可用")
            
            # 创建新会话
            await self.zap.create_new_session(f"scan_{scan_id}")
            
            # 配置认证
            if self.config.authentication_config:
                await self.zap.configure_authentication(target_url, self.config.authentication_config)
            
            # 1. 爬虫扫描
            logger.info("执行爬虫扫描...")
            await self.zap.spider_scan(target_url, self.config.max_scan_depth)
            
            # 2. AJAX爬虫扫描
            logger.info("执行AJAX爬虫扫描...")
            await self.zap.ajax_spider_scan(target_url)
            
            # 3. 被动扫描
            logger.info("执行被动扫描...")
            await self.zap.passive_scan(target_url)
            
            # 4. 主动扫描
            logger.info("执行主动扫描...")
            await self.zap.active_scan(target_url)
            
            # 获取漏洞信息
            vulnerabilities = self.zap.get_alerts(target_url)
            
            # 统计漏洞数量
            vulnerability_counts = self._count_vulnerabilities_by_severity(vulnerabilities)
            
            # 生成报告
            report_path = await self.zap.generate_report("html")
            
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            result = ScanResult(
                scan_id=scan_id,
                target_url=target_url,
                scan_type=ScanType.FULL,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                status="COMPLETED",
                vulnerabilities=vulnerabilities,
                total_vulnerabilities=len(vulnerabilities),
                critical_count=vulnerability_counts["critical"],
                high_count=vulnerability_counts["high"],
                medium_count=vulnerability_counts["medium"],
                low_count=vulnerability_counts["low"],
                info_count=vulnerability_counts["info"],
                urls_scanned=self._get_urls_scanned_count(),
                report_path=report_path
            )
            
            logger.info(f"安全扫描完成: {scan_id}, 发现 {len(vulnerabilities)} 个漏洞")
            return result
            
        except Exception as e:
            logger.error(f"安全扫描异常: {scan_id}, 错误: {str(e)}")
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            return ScanResult(
                scan_id=scan_id,
                target_url=target_url,
                scan_type=ScanType.FULL,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                status="ERROR",
                vulnerabilities=[],
                total_vulnerabilities=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                urls_scanned=0
            )
    
    async def baseline_scan(self, target_url: str, scan_id: str) -> ScanResult:
        """执行基线扫描"""
        start_time = datetime.now()
        
        try:
            logger.info(f"开始基线安全扫描: {target_url}")
            
            # 检查ZAP状态
            if not await self.zap.check_zap_status():
                raise TestExecutionError("ZAP服务不可用")
            
            # 创建新会话
            await self.zap.create_new_session(f"baseline_{scan_id}")
            
            # 爬虫扫描
            await self.zap.spider_scan(target_url, 3)  # 限制深度
            
            # 被动扫描
            await self.zap.passive_scan(target_url)
            
            # 获取漏洞信息
            vulnerabilities = self.zap.get_alerts(target_url)
            
            # 过滤低风险漏洞
            filtered_vulnerabilities = [
                v for v in vulnerabilities 
                if v.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM]
            ]
            
            vulnerability_counts = self._count_vulnerabilities_by_severity(filtered_vulnerabilities)
            
            # 生成报告
            report_path = await self.zap.generate_report("html")
            
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            result = ScanResult(
                scan_id=scan_id,
                target_url=target_url,
                scan_type=ScanType.BASELINE,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                status="COMPLETED",
                vulnerabilities=filtered_vulnerabilities,
                total_vulnerabilities=len(filtered_vulnerabilities),
                critical_count=vulnerability_counts["critical"],
                high_count=vulnerability_counts["high"],
                medium_count=vulnerability_counts["medium"],
                low_count=vulnerability_counts["low"],
                info_count=vulnerability_counts["info"],
                urls_scanned=self._get_urls_scanned_count(),
                report_path=report_path
            )
            
            logger.info(f"基线扫描完成: {scan_id}, 发现 {len(filtered_vulnerabilities)} 个中高风险漏洞")
            return result
            
        except Exception as e:
            logger.error(f"基线扫描异常: {scan_id}, 错误: {str(e)}")
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            return ScanResult(
                scan_id=scan_id,
                target_url=target_url,
                scan_type=ScanType.BASELINE,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                status="ERROR",
                vulnerabilities=[],
                total_vulnerabilities=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                info_count=0,
                urls_scanned=0
            )
    
    async def network_scan(self, target: str, scan_id: str) -> Dict[str, Any]:
        """执行网络扫描"""
        logger.info(f"开始网络扫描: {target}")
        
        try:
            # 端口扫描
            port_scan_result = await self.nmap.port_scan(target)
            
            # 服务扫描
            service_scan_result = await self.nmap.service_scan(target)
            
            # 漏洞扫描
            vuln_scan_result = await self.nmap.vulnerability_scan(target)
            
            result = {
                "scan_id": scan_id,
                "target": target,
                "timestamp": datetime.now().isoformat(),
                "port_scan": port_scan_result,
                "service_scan": service_scan_result,
                "vulnerability_scan": vuln_scan_result
            }
            
            logger.info(f"网络扫描完成: {scan_id}")
            return result
            
        except Exception as e:
            logger.error(f"网络扫描异常: {scan_id}, 错误: {str(e)}")
            return {
                "scan_id": scan_id,
                "target": target,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _count_vulnerabilities_by_severity(self, vulnerabilities: List[Vulnerability]) -> Dict[str, int]:
        """按严重程度统计漏洞数量"""
        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        for vuln in vulnerabilities:
            counts[vuln.severity.value] += 1
        
        return counts
    
    def _get_urls_scanned_count(self) -> int:
        """获取扫描的URL数量"""
        try:
            result = self.zap._make_api_request("core/view/urls")
            return len(result.get("urls", []))
        except:
            return 0
    
    def create_sample_security_config(self) -> SecurityConfig:
        """创建示例安全配置"""
        return SecurityConfig(
            zap_proxy_host="127.0.0.1",
            zap_proxy_port=8080,
            scan_timeout=1800,  # 30分钟
            max_scan_depth=3,
            thread_count=3,
            authentication_config={
                "type": "form",
                "login_url": "https://example.com/login",
                "username_field": "username",
                "password_field": "password",
                "username": "testuser",
                "password": "testpass"
            }
        )


# 导出主要类和函数
__all__ = [
    "SecurityTestIntegration",
    "SecurityConfig",
    "Vulnerability",
    "ScanResult",
    "SeverityLevel",
    "ScanType",
    "VulnerabilityType"
]