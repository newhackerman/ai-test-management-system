"""
CI/CD集成模块
支持Jenkins、GitLab CI等平台集成，实现自动化测试的触发和执行
"""

import asyncio
import json
import os
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import yaml

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


class CIPlatform(Enum):
    """CI平台类型"""
    JENKINS = "jenkins"
    GITLAB_CI = "gitlab_ci"
    GITHUB_ACTIONS = "github_actions"
    AZURE_DEVOPS = "azure_devops"
    BAMBOO = "bamboo"


class BuildStatus(Enum):
    """构建状态"""
    SUCCESS = "success"
    FAILURE = "failure"
    UNSTABLE = "unstable"
    ABORTED = "aborted"
    NOT_BUILT = "not_built"
    BUILDING = "building"
    PENDING = "pending"


class TriggerType(Enum):
    """触发类型"""
    MANUAL = "manual"
    SCM_CHANGE = "scm_change"
    SCHEDULED = "scheduled"
    UPSTREAM = "upstream"
    WEBHOOK = "webhook"


@dataclass
class CIConfig:
    """CI配置"""
    platform: CIPlatform
    server_url: str
    username: Optional[str] = None
    password: Optional[str] = None
    api_token: Optional[str] = None
    project_id: Optional[str] = None
    job_name: Optional[str] = None
    timeout: int = 3600  # 超时时间(秒)
    verify_ssl: bool = True
    headers: Optional[Dict[str, str]] = None


@dataclass
class BuildParameter:
    """构建参数"""
    name: str
    value: str
    description: Optional[str] = None


@dataclass
class TestTriggerConfig:
    """测试触发配置"""
    test_plan_id: Optional[int] = None
    test_suite_ids: Optional[List[int]] = None
    test_environment: str = "qa"
    browser: str = "chrome"
    parallel_count: int = 1
    retry_count: int = 0
    notification_enabled: bool = True
    report_format: str = "html"
    custom_parameters: Optional[Dict[str, str]] = None


@dataclass
class BuildInfo:
    """构建信息"""
    build_id: str
    build_number: int
    job_name: str
    status: BuildStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[int]
    url: str
    parameters: Optional[List[BuildParameter]] = None
    artifacts: Optional[List[str]] = None
    test_results: Optional[Dict[str, Any]] = None


@dataclass
class WebhookPayload:
    """Webhook负载"""
    event_type: str
    repository: str
    branch: str
    commit_id: str
    commit_message: str
    author: str
    timestamp: datetime
    build_url: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None


class JenkinsIntegration:
    """Jenkins集成"""
    
    def __init__(self, config: CIConfig):
        self.config = config
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            connector=aiohttp.TCPConnector(verify_ssl=self.config.verify_ssl)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        headers = {}
        
        if self.config.api_token:
            # 使用API Token
            auth_string = f"{self.config.username}:{self.config.api_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            headers['Authorization'] = f'Basic {auth_b64}'
        elif self.config.username and self.config.password:
            # 使用用户名密码
            auth_string = f"{self.config.username}:{self.config.password}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            headers['Authorization'] = f'Basic {auth_b64}'
        
        if self.config.headers:
            headers.update(self.config.headers)
        
        return headers
    
    async def trigger_build(
        self,
        job_name: str,
        parameters: Optional[List[BuildParameter]] = None
    ) -> str:
        """触发构建"""
        if not self.session:
            raise RuntimeError("Session未初始化")
        
        headers = self._get_auth_headers()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        # 构建URL
        if parameters:
            url = f"{self.config.server_url}/job/{job_name}/buildWithParameters"
            data = {}
            for param in parameters:
                data[param.name] = param.value
        else:
            url = f"{self.config.server_url}/job/{job_name}/build"
            data = {}
        
        try:
            async with self.session.post(url, headers=headers, data=data) as response:
                if response.status == 201:
                    # 获取队列项目ID
                    location = response.headers.get('Location', '')
                    queue_id = location.split('/')[-2] if location else None
                    
                    logger.info(f"Jenkins构建已触发: {job_name}, 队列ID: {queue_id}")
                    return queue_id or "unknown"
                else:
                    error_text = await response.text()
                    raise TestExecutionError(f"触发Jenkins构建失败: {response.status}, {error_text}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Jenkins API请求失败: {str(e)}")
            raise TestExecutionError(f"Jenkins API请求失败: {str(e)}")
    
    async def get_build_info(self, job_name: str, build_number: int) -> BuildInfo:
        """获取构建信息"""
        if not self.session:
            raise RuntimeError("Session未初始化")
        
        headers = self._get_auth_headers()
        url = f"{self.config.server_url}/job/{job_name}/{build_number}/api/json"
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 解析构建信息
                    status_mapping = {
                        'SUCCESS': BuildStatus.SUCCESS,
                        'FAILURE': BuildStatus.FAILURE,
                        'UNSTABLE': BuildStatus.UNSTABLE,
                        'ABORTED': BuildStatus.ABORTED,
                        'NOT_BUILT': BuildStatus.NOT_BUILT
                    }
                    
                    result = data.get('result', 'BUILDING')
                    status = status_mapping.get(result, BuildStatus.BUILDING)
                    
                    start_time = datetime.fromtimestamp(data['timestamp'] / 1000)
                    duration = data.get('duration', 0)
                    end_time = None
                    if duration > 0:
                        end_time = datetime.fromtimestamp((data['timestamp'] + duration) / 1000)
                    
                    # 解析参数
                    parameters = []
                    actions = data.get('actions', [])
                    for action in actions:
                        if action.get('_class') == 'hudson.model.ParametersAction':
                            for param in action.get('parameters', []):
                                parameters.append(BuildParameter(
                                    name=param.get('name', ''),
                                    value=str(param.get('value', '')),
                                    description=param.get('description')
                                ))
                    
                    # 解析构件
                    artifacts = []
                    for artifact in data.get('artifacts', []):
                        artifacts.append(artifact.get('relativePath', ''))
                    
                    build_info = BuildInfo(
                        build_id=str(data['id']),
                        build_number=data['number'],
                        job_name=job_name,
                        status=status,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration // 1000 if duration > 0 else None,
                        url=data['url'],
                        parameters=parameters if parameters else None,
                        artifacts=artifacts if artifacts else None
                    )
                    
                    return build_info
                else:
                    error_text = await response.text()
                    raise TestExecutionError(f"获取Jenkins构建信息失败: {response.status}, {error_text}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Jenkins API请求失败: {str(e)}")
            raise TestExecutionError(f"Jenkins API请求失败: {str(e)}")
    
    async def wait_for_build_completion(
        self,
        job_name: str,
        build_number: int,
        poll_interval: int = 30
    ) -> BuildInfo:
        """等待构建完成"""
        logger.info(f"等待Jenkins构建完成: {job_name}#{build_number}")
        
        while True:
            build_info = await self.get_build_info(job_name, build_number)
            
            if build_info.status != BuildStatus.BUILDING:
                logger.info(f"Jenkins构建完成: {job_name}#{build_number}, 状态: {build_info.status.value}")
                return build_info
            
            logger.debug(f"Jenkins构建进行中: {job_name}#{build_number}")
            await asyncio.sleep(poll_interval)
    
    async def get_console_output(self, job_name: str, build_number: int) -> str:
        """获取控制台输出"""
        if not self.session:
            raise RuntimeError("Session未初始化")
        
        headers = self._get_auth_headers()
        url = f"{self.config.server_url}/job/{job_name}/{build_number}/consoleText"
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    error_text = await response.text()
                    raise TestExecutionError(f"获取Jenkins控制台输出失败: {response.status}, {error_text}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Jenkins API请求失败: {str(e)}")
            raise TestExecutionError(f"Jenkins API请求失败: {str(e)}")
    
    async def download_artifact(
        self,
        job_name: str,
        build_number: int,
        artifact_path: str,
        local_path: str
    ):
        """下载构件"""
        if not self.session:
            raise RuntimeError("Session未初始化")
        
        headers = self._get_auth_headers()
        url = f"{self.config.server_url}/job/{job_name}/{build_number}/artifact/{artifact_path}"
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    # 确保本地目录存在
                    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(local_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    
                    logger.info(f"Jenkins构件下载完成: {artifact_path} -> {local_path}")
                else:
                    error_text = await response.text()
                    raise TestExecutionError(f"下载Jenkins构件失败: {response.status}, {error_text}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Jenkins API请求失败: {str(e)}")
            raise TestExecutionError(f"Jenkins API请求失败: {str(e)}")


class GitLabCIIntegration:
    """GitLab CI集成"""
    
    def __init__(self, config: CIConfig):
        self.config = config
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            connector=aiohttp.TCPConnector(verify_ssl=self.config.verify_ssl)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        headers = {}
        
        if self.config.api_token:
            headers['PRIVATE-TOKEN'] = self.config.api_token
        
        if self.config.headers:
            headers.update(self.config.headers)
        
        return headers
    
    async def trigger_pipeline(
        self,
        project_id: str,
        ref: str = "main",
        variables: Optional[Dict[str, str]] = None
    ) -> str:
        """触发流水线"""
        if not self.session:
            raise RuntimeError("Session未初始化")
        
        headers = self._get_auth_headers()
        headers['Content-Type'] = 'application/json'
        
        url = f"{self.config.server_url}/api/v4/projects/{project_id}/pipeline"
        
        data = {"ref": ref}
        if variables:
            data["variables"] = [
                {"key": key, "value": value} for key, value in variables.items()
            ]
        
        try:
            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status == 201:
                    result = await response.json()
                    pipeline_id = str(result['id'])
                    
                    logger.info(f"GitLab流水线已触发: {project_id}, 流水线ID: {pipeline_id}")
                    return pipeline_id
                else:
                    error_text = await response.text()
                    raise TestExecutionError(f"触发GitLab流水线失败: {response.status}, {error_text}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"GitLab API请求失败: {str(e)}")
            raise TestExecutionError(f"GitLab API请求失败: {str(e)}")
    
    async def get_pipeline_status(self, project_id: str, pipeline_id: str) -> Dict[str, Any]:
        """获取流水线状态"""
        if not self.session:
            raise RuntimeError("Session未初始化")
        
        headers = self._get_auth_headers()
        url = f"{self.config.server_url}/api/v4/projects/{project_id}/pipelines/{pipeline_id}"
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise TestExecutionError(f"获取GitLab流水线状态失败: {response.status}, {error_text}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"GitLab API请求失败: {str(e)}")
            raise TestExecutionError(f"GitLab API请求失败: {str(e)}")
    
    async def wait_for_pipeline_completion(
        self,
        project_id: str,
        pipeline_id: str,
        poll_interval: int = 30
    ) -> Dict[str, Any]:
        """等待流水线完成"""
        logger.info(f"等待GitLab流水线完成: {project_id}/{pipeline_id}")
        
        while True:
            pipeline_info = await self.get_pipeline_status(project_id, pipeline_id)
            status = pipeline_info.get('status', 'running')
            
            if status in ['success', 'failed', 'canceled', 'skipped']:
                logger.info(f"GitLab流水线完成: {project_id}/{pipeline_id}, 状态: {status}")
                return pipeline_info
            
            logger.debug(f"GitLab流水线进行中: {project_id}/{pipeline_id}, 状态: {status}")
            await asyncio.sleep(poll_interval)


class CICDIntegration:
    """CI/CD集成主类"""
    
    def __init__(self, config: CIConfig):
        self.config = config
        self.integration = self._create_integration()
    
    def _create_integration(self):
        """创建具体的集成实例"""
        if self.config.platform == CIPlatform.JENKINS:
            return JenkinsIntegration(self.config)
        elif self.config.platform == CIPlatform.GITLAB_CI:
            return GitLabCIIntegration(self.config)
        else:
            raise ConfigurationError(f"不支持的CI平台: {self.config.platform}")
    
    async def trigger_test_execution(
        self,
        trigger_config: TestTriggerConfig,
        webhook_payload: Optional[WebhookPayload] = None
    ) -> str:
        """触发测试执行"""
        logger.info(f"触发测试执行: {self.config.platform.value}")
        
        # 构建参数
        parameters = []
        
        if trigger_config.test_plan_id:
            parameters.append(BuildParameter("TEST_PLAN_ID", str(trigger_config.test_plan_id)))
        
        if trigger_config.test_suite_ids:
            suite_ids = ",".join(map(str, trigger_config.test_suite_ids))
            parameters.append(BuildParameter("TEST_SUITE_IDS", suite_ids))
        
        parameters.extend([
            BuildParameter("TEST_ENVIRONMENT", trigger_config.test_environment),
            BuildParameter("BROWSER", trigger_config.browser),
            BuildParameter("PARALLEL_COUNT", str(trigger_config.parallel_count)),
            BuildParameter("RETRY_COUNT", str(trigger_config.retry_count)),
            BuildParameter("REPORT_FORMAT", trigger_config.report_format)
        ])
        
        # 添加自定义参数
        if trigger_config.custom_parameters:
            for key, value in trigger_config.custom_parameters.items():
                parameters.append(BuildParameter(key, value))
        
        # 添加Webhook信息
        if webhook_payload:
            parameters.extend([
                BuildParameter("REPOSITORY", webhook_payload.repository),
                BuildParameter("BRANCH", webhook_payload.branch),
                BuildParameter("COMMIT_ID", webhook_payload.commit_id),
                BuildParameter("COMMIT_MESSAGE", webhook_payload.commit_message),
                BuildParameter("AUTHOR", webhook_payload.author)
            ])
        
        # 根据平台类型触发
        if self.config.platform == CIPlatform.JENKINS:
            async with self.integration as jenkins:
                return await jenkins.trigger_build(
                    self.config.job_name or "test-execution",
                    parameters
                )
        elif self.config.platform == CIPlatform.GITLAB_CI:
            variables = {param.name: param.value for param in parameters}
            async with self.integration as gitlab:
                return await gitlab.trigger_pipeline(
                    self.config.project_id,
                    webhook_payload.branch if webhook_payload else "main",
                    variables
                )
        else:
            raise ConfigurationError(f"不支持的CI平台: {self.config.platform}")
    
    async def monitor_test_execution(
        self,
        execution_id: str,
        poll_interval: int = 30
    ) -> BuildInfo:
        """监控测试执行"""
        logger.info(f"监控测试执行: {execution_id}")
        
        if self.config.platform == CIPlatform.JENKINS:
            async with self.integration as jenkins:
                # 对于Jenkins，需要先获取构建号
                # 这里简化处理，假设execution_id就是构建号
                build_number = int(execution_id) if execution_id.isdigit() else 1
                return await jenkins.wait_for_build_completion(
                    self.config.job_name or "test-execution",
                    build_number,
                    poll_interval
                )
        elif self.config.platform == CIPlatform.GITLAB_CI:
            async with self.integration as gitlab:
                pipeline_info = await gitlab.wait_for_pipeline_completion(
                    self.config.project_id,
                    execution_id,
                    poll_interval
                )
                
                # 转换为BuildInfo格式
                status_mapping = {
                    'success': BuildStatus.SUCCESS,
                    'failed': BuildStatus.FAILURE,
                    'canceled': BuildStatus.ABORTED,
                    'skipped': BuildStatus.NOT_BUILT
                }
                
                status = status_mapping.get(pipeline_info.get('status'), BuildStatus.FAILURE)
                
                return BuildInfo(
                    build_id=execution_id,
                    build_number=int(pipeline_info.get('id', 0)),
                    job_name=self.config.project_id,
                    status=status,
                    start_time=datetime.fromisoformat(pipeline_info.get('created_at', datetime.now().isoformat())),
                    end_time=datetime.fromisoformat(pipeline_info.get('finished_at', datetime.now().isoformat())) if pipeline_info.get('finished_at') else None,
                    duration=pipeline_info.get('duration'),
                    url=pipeline_info.get('web_url', '')
                )
        else:
            raise ConfigurationError(f"不支持的CI平台: {self.config.platform}")
    
    async def get_test_results(self, execution_id: str) -> Dict[str, Any]:
        """获取测试结果"""
        logger.info(f"获取测试结果: {execution_id}")
        
        if self.config.platform == CIPlatform.JENKINS:
            async with self.integration as jenkins:
                build_number = int(execution_id) if execution_id.isdigit() else 1
                
                # 获取构建信息
                build_info = await jenkins.get_build_info(
                    self.config.job_name or "test-execution",
                    build_number
                )
                
                # 获取控制台输出
                console_output = await jenkins.get_console_output(
                    self.config.job_name or "test-execution",
                    build_number
                )
                
                return {
                    "build_info": asdict(build_info),
                    "console_output": console_output,
                    "artifacts": build_info.artifacts or []
                }
        elif self.config.platform == CIPlatform.GITLAB_CI:
            async with self.integration as gitlab:
                pipeline_info = await gitlab.get_pipeline_status(
                    self.config.project_id,
                    execution_id
                )
                
                return {
                    "pipeline_info": pipeline_info,
                    "jobs": []  # 可以进一步获取作业详情
                }
        else:
            raise ConfigurationError(f"不支持的CI平台: {self.config.platform}")
    
    def create_webhook_payload(self, request_data: Dict[str, Any]) -> WebhookPayload:
        """创建Webhook负载"""
        if self.config.platform == CIPlatform.JENKINS:
            # Jenkins webhook格式
            return WebhookPayload(
                event_type=request_data.get('event_type', 'push'),
                repository=request_data.get('repository', ''),
                branch=request_data.get('branch', 'main'),
                commit_id=request_data.get('commit_id', ''),
                commit_message=request_data.get('commit_message', ''),
                author=request_data.get('author', ''),
                timestamp=datetime.now(),
                build_url=request_data.get('build_url'),
                custom_data=request_data.get('custom_data')
            )
        elif self.config.platform == CIPlatform.GITLAB_CI:
            # GitLab webhook格式
            return WebhookPayload(
                event_type=request_data.get('object_kind', 'push'),
                repository=request_data.get('project', {}).get('path_with_namespace', ''),
                branch=request_data.get('ref', '').replace('refs/heads/', ''),
                commit_id=request_data.get('after', ''),
                commit_message=request_data.get('commits', [{}])[0].get('message', '') if request_data.get('commits') else '',
                author=request_data.get('user_name', ''),
                timestamp=datetime.now(),
                custom_data=request_data
            )
        else:
            # 通用格式
            return WebhookPayload(
                event_type=request_data.get('event_type', 'unknown'),
                repository=request_data.get('repository', ''),
                branch=request_data.get('branch', 'main'),
                commit_id=request_data.get('commit_id', ''),
                commit_message=request_data.get('commit_message', ''),
                author=request_data.get('author', ''),
                timestamp=datetime.now(),
                custom_data=request_data
            )
    
    def generate_jenkins_pipeline_script(self, trigger_config: TestTriggerConfig) -> str:
        """生成Jenkins流水线脚本"""
        script = f"""
pipeline {{
    agent any
    
    parameters {{
        string(name: 'TEST_PLAN_ID', defaultValue: '{trigger_config.test_plan_id or ""}', description: '测试计划ID')
        string(name: 'TEST_ENVIRONMENT', defaultValue: '{trigger_config.test_environment}', description: '测试环境')
        choice(name: 'BROWSER', choices: ['chrome', 'firefox', 'safari'], description: '浏览器类型')
        string(name: 'PARALLEL_COUNT', defaultValue: '{trigger_config.parallel_count}', description: '并发数')
    }}
    
    stages {{
        stage('准备环境') {{
            steps {{
                echo "准备测试环境: ${{params.TEST_ENVIRONMENT}}"
                // 环境准备脚本
            }}
        }}
        
        stage('执行测试') {{
            steps {{
                script {{
                    echo "执行测试计划: ${{params.TEST_PLAN_ID}}"
                    // 调用测试管理系统API执行测试
                    sh '''
                        curl -X POST "http://testmanager-api/api/v1/test-executions/trigger" \\
                             -H "Content-Type: application/json" \\
                             -d "{{
                                 \\"test_plan_id\\": \\"${{params.TEST_PLAN_ID}}\\",
                                 \\"environment\\": \\"${{params.TEST_ENVIRONMENT}}\\",
                                 \\"browser\\": \\"${{params.BROWSER}}\\",
                                 \\"parallel_count\\": ${{params.PARALLEL_COUNT}}
                             }}"
                    '''
                }}
            }}
        }}
        
        stage('生成报告') {{
            steps {{
                echo "生成测试报告"
                // 生成和发布测试报告
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'test-reports',
                    reportFiles: 'index.html',
                    reportName: '测试报告'
                ])
            }}
        }}
    }}
    
    post {{
        always {{
            echo "清理工作空间"
            cleanWs()
        }}
        success {{
            echo "测试执行成功"
            // 发送成功通知
        }}
        failure {{
            echo "测试执行失败"
            // 发送失败通知
        }}
    }}
}}
"""
        return script
    
    def generate_gitlab_ci_config(self, trigger_config: TestTriggerConfig) -> str:
        """生成GitLab CI配置"""
        config = {
            "stages": ["test", "report"],
            "variables": {
                "TEST_ENVIRONMENT": trigger_config.test_environment,
                "BROWSER": trigger_config.browser,
                "PARALLEL_COUNT": str(trigger_config.parallel_count)
            },
            "test_execution": {
                "stage": "test",
                "script": [
                    "echo '执行自动化测试'",
                    "curl -X POST \"$TESTMANAGER_API_URL/api/v1/test-executions/trigger\" -H \"Content-Type: application/json\" -d '{\"test_plan_id\": \"$TEST_PLAN_ID\", \"environment\": \"$TEST_ENVIRONMENT\", \"browser\": \"$BROWSER\", \"parallel_count\": $PARALLEL_COUNT}'"
                ],
                "artifacts": {
                    "reports": {
                        "junit": "test-results/*.xml"
                    },
                    "paths": ["test-reports/"]
                }
            },
            "generate_report": {
                "stage": "report",
                "script": [
                    "echo '生成测试报告'",
                    "# 生成Allure报告或其他格式报告"
                ],
                "artifacts": {
                    "paths": ["allure-report/"],
                    "expire_in": "1 week"
                },
                "only": ["main", "develop"]
            }
        }
        
        return yaml.dump(config, default_flow_style=False, allow_unicode=True)
    
    def create_sample_jenkins_config(self) -> CIConfig:
        """创建示例Jenkins配置"""
        return CIConfig(
            platform=CIPlatform.JENKINS,
            server_url="http://jenkins.example.com:8080",
            username="testuser",
            api_token="your-api-token",
            job_name="testmanager-automation",
            timeout=3600
        )
    
    def create_sample_gitlab_config(self) -> CIConfig:
        """创建示例GitLab配置"""
        return CIConfig(
            platform=CIPlatform.GITLAB_CI,
            server_url="https://gitlab.example.com",
            api_token="your-gitlab-token",
            project_id="123",
            timeout=3600
        )


# 导出主要类和函数
__all__ = [
    "CICDIntegration",
    "CIConfig",
    "TestTriggerConfig",
    "BuildInfo",
    "WebhookPayload",
    "CIPlatform",
    "BuildStatus",
    "TriggerType"
]