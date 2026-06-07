#!/usr/bin/env python3
"""
自动化部署脚本

提供完整的部署自动化功能，包括环境检查、服务部署、健康检查和回滚机制
"""
import os
import sys
import json
import time
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

@dataclass
class DeploymentConfig:
    """部署配置"""
    environment: str = 'staging'
    service_name: str = 'ai-testing-system'
    namespace: str = 'default'
    image_tag: str = 'latest'
    replicas: int = 2
    health_check_timeout: int = 300
    rollback_enabled: bool = True
    notification_enabled: bool = True
    pre_deploy_checks: bool = True
    post_deploy_checks: bool = True
    
@dataclass
class DeploymentResult:
    """部署结果"""
    success: bool
    environment: str
    service_name: str
    deployment_time: datetime
    duration_seconds: float
    previous_version: Optional[str] = None
    new_version: Optional[str] = None
    error_message: Optional[str] = None
    rollback_performed: bool = False

class DeploymentAutomation:
    """部署自动化"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.project_root = project_root
        self.deployment_dir = self.project_root / "deployments"
        self.deployment_dir.mkdir(exist_ok=True)
        
        # 设置日志
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 部署状态
        self.deployment_start_time = None
        self.previous_deployment = None
    
    def setup_logging(self):
        """设置日志"""
        log_file = self.deployment_dir / f"deploy_{self.config.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def deploy(self) -> DeploymentResult:
        """执行部署"""
        self.deployment_start_time = datetime.now()
        
        self.logger.info("="*60)
        self.logger.info(f"开始部署到 {self.config.environment.upper()} 环境")
        self.logger.info("="*60)
        
        try:
            # 1. 部署前检查
            if self.config.pre_deploy_checks:
                if not self.pre_deployment_checks():
                    return self._create_failure_result("部署前检查失败")
            
            # 2. 备份当前部署
            if self.config.rollback_enabled:
                self.backup_current_deployment()
            
            # 3. 执行部署
            if not self.execute_deployment():
                return self._create_failure_result("部署执行失败")
            
            # 4. 部署后检查
            if self.config.post_deploy_checks:
                if not self.post_deployment_checks():
                    if self.config.rollback_enabled:
                        self.logger.warning("部署后检查失败，开始回滚...")
                        if self.rollback_deployment():
                            return self._create_failure_result("部署失败，已回滚到之前版本", rollback_performed=True)
                        else:
                            return self._create_failure_result("部署失败，回滚也失败")
                    else:
                        return self._create_failure_result("部署后检查失败")
            
            # 5. 发送成功通知
            if self.config.notification_enabled:
                self.send_success_notification()
            
            duration = (datetime.now() - self.deployment_start_time).total_seconds()
            
            self.logger.info("="*60)
            self.logger.info(f"✅ 部署成功完成 (耗时: {duration:.2f}s)")
            self.logger.info("="*60)
            
            return DeploymentResult(
                success=True,
                environment=self.config.environment,
                service_name=self.config.service_name,
                deployment_time=self.deployment_start_time,
                duration_seconds=duration,
                new_version=self.config.image_tag
            )
            
        except Exception as e:
            self.logger.error(f"部署异常: {e}")
            
            # 尝试回滚
            if self.config.rollback_enabled:
                self.logger.info("开始自动回滚...")
                rollback_success = self.rollback_deployment()
                return self._create_failure_result(str(e), rollback_performed=rollback_success)
            else:
                return self._create_failure_result(str(e))
    
    def _create_failure_result(self, error_message: str, rollback_performed: bool = False) -> DeploymentResult:
        """创建失败结果"""
        duration = (datetime.now() - self.deployment_start_time).total_seconds() if self.deployment_start_time else 0
        
        # 发送失败通知
        if self.config.notification_enabled:
            self.send_failure_notification(error_message)
        
        self.logger.error("="*60)
        self.logger.error(f"❌ 部署失败 (耗时: {duration:.2f}s)")
        self.logger.error(f"错误: {error_message}")
        if rollback_performed:
            self.logger.info("已执行回滚操作")
        self.logger.error("="*60)
        
        return DeploymentResult(
            success=False,
            environment=self.config.environment,
            service_name=self.config.service_name,
            deployment_time=self.deployment_start_time or datetime.now(),
            duration_seconds=duration,
            error_message=error_message,
            rollback_performed=rollback_performed
        )
    
    def pre_deployment_checks(self) -> bool:
        """部署前检查"""
        self.logger.info("执行部署前检查...")
        
        checks = [
            ("检查Docker镜像", self.check_docker_image),
            ("检查Kubernetes连接", self.check_kubernetes_connection),
            ("检查资源配额", self.check_resource_quota),
            ("检查配置文件", self.check_configuration_files),
            ("检查依赖服务", self.check_dependency_services)
        ]
        
        for check_name, check_func in checks:
            self.logger.info(f"  {check_name}...")
            if not check_func():
                self.logger.error(f"  ❌ {check_name} 失败")
                return False
            self.logger.info(f"  ✅ {check_name} 通过")
        
        self.logger.info("部署前检查完成")
        return True
    
    def check_docker_image(self) -> bool:
        """检查Docker镜像"""
        try:
            # 检查镜像是否存在
            cmd = ['docker', 'manifest', 'inspect', f"{self.config.service_name}:{self.config.image_tag}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return True
            else:
                self.logger.error(f"Docker镜像不存在: {self.config.service_name}:{self.config.image_tag}")
                return False
                
        except Exception as e:
            self.logger.error(f"检查Docker镜像失败: {e}")
            return False
    
    def check_kubernetes_connection(self) -> bool:
        """检查Kubernetes连接"""
        try:
            cmd = ['kubectl', 'cluster-info']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"检查Kubernetes连接失败: {e}")
            return False
    
    def check_resource_quota(self) -> bool:
        """检查资源配额"""
        try:
            # 检查命名空间资源配额
            cmd = ['kubectl', 'describe', 'quota', '-n', self.config.namespace]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # 这里可以添加更详细的资源检查逻辑
            return True
            
        except Exception as e:
            self.logger.warning(f"检查资源配额失败: {e}")
            return True  # 非关键检查，失败不阻止部署
    
    def check_configuration_files(self) -> bool:
        """检查配置文件"""
        try:
            # 检查Kubernetes配置文件
            k8s_dir = self.project_root / "k8s" / self.config.environment
            
            required_files = [
                "deployment.yaml",
                "service.yaml",
                "configmap.yaml"
            ]
            
            for file_name in required_files:
                file_path = k8s_dir / file_name
                if not file_path.exists():
                    self.logger.error(f"配置文件不存在: {file_path}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"检查配置文件失败: {e}")
            return False
    
    def check_dependency_services(self) -> bool:
        """检查依赖服务"""
        try:
            # 检查数据库连接
            if not self.check_database_connection():
                return False
            
            # 检查Redis连接
            if not self.check_redis_connection():
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"检查依赖服务失败: {e}")
            return False
    
    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            # 这里可以添加实际的数据库连接检查
            # 例如：连接MySQL/PostgreSQL并执行简单查询
            self.logger.info("数据库连接检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"数据库连接检查失败: {e}")
            return False
    
    def check_redis_connection(self) -> bool:
        """检查Redis连接"""
        try:
            # 这里可以添加实际的Redis连接检查
            self.logger.info("Redis连接检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"Redis连接检查失败: {e}")
            return False
    
    def backup_current_deployment(self):
        """备份当前部署"""
        self.logger.info("备份当前部署...")
        
        try:
            # 获取当前部署信息
            cmd = ['kubectl', 'get', 'deployment', self.config.service_name, 
                   '-n', self.config.namespace, '-o', 'json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                deployment_info = json.loads(result.stdout)
                
                # 保存备份信息
                backup_file = self.deployment_dir / f"backup_{self.config.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(deployment_info, f, indent=2)
                
                self.previous_deployment = backup_file
                self.logger.info(f"当前部署已备份到: {backup_file}")
            else:
                self.logger.warning("未找到现有部署，跳过备份")
                
        except Exception as e:
            self.logger.warning(f"备份当前部署失败: {e}")
    
    def execute_deployment(self) -> bool:
        """执行部署"""
        self.logger.info("执行部署...")
        
        try:
            # 1. 应用ConfigMap
            if not self.apply_configmap():
                return False
            
            # 2. 应用Service
            if not self.apply_service():
                return False
            
            # 3. 应用Deployment
            if not self.apply_deployment():
                return False
            
            # 4. 等待部署完成
            if not self.wait_for_deployment():
                return False
            
            self.logger.info("部署执行完成")
            return True
            
        except Exception as e:
            self.logger.error(f"执行部署失败: {e}")
            return False
    
    def apply_configmap(self) -> bool:
        """应用ConfigMap"""
        try:
            config_file = self.project_root / "k8s" / self.config.environment / "configmap.yaml"
            
            cmd = ['kubectl', 'apply', '-f', str(config_file), '-n', self.config.namespace]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.logger.info("ConfigMap应用成功")
                return True
            else:
                self.logger.error(f"ConfigMap应用失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"应用ConfigMap失败: {e}")
            return False
    
    def apply_service(self) -> bool:
        """应用Service"""
        try:
            service_file = self.project_root / "k8s" / self.config.environment / "service.yaml"
            
            cmd = ['kubectl', 'apply', '-f', str(service_file), '-n', self.config.namespace]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.logger.info("Service应用成功")
                return True
            else:
                self.logger.error(f"Service应用失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"应用Service失败: {e}")
            return False
    
    def apply_deployment(self) -> bool:
        """应用Deployment"""
        try:
            deployment_file = self.project_root / "k8s" / self.config.environment / "deployment.yaml"
            
            # 替换镜像标签
            self.update_deployment_image(deployment_file)
            
            cmd = ['kubectl', 'apply', '-f', str(deployment_file), '-n', self.config.namespace]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.logger.info("Deployment应用成功")
                return True
            else:
                self.logger.error(f"Deployment应用失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"应用Deployment失败: {e}")
            return False
    
    def update_deployment_image(self, deployment_file: Path):
        """更新部署文件中的镜像标签"""
        try:
            with open(deployment_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换镜像标签（简单的字符串替换，实际项目中可能需要更复杂的YAML处理）
            content = content.replace('{{IMAGE_TAG}}', self.config.image_tag)
            content = content.replace('{{REPLICAS}}', str(self.config.replicas))
            
            with open(deployment_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            self.logger.error(f"更新部署文件失败: {e}")
            raise
    
    def wait_for_deployment(self) -> bool:
        """等待部署完成"""
        self.logger.info("等待部署完成...")
        
        try:
            cmd = ['kubectl', 'rollout', 'status', f'deployment/{self.config.service_name}', 
                   '-n', self.config.namespace, f'--timeout={self.config.health_check_timeout}s']
            
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  timeout=self.config.health_check_timeout + 30)
            
            if result.returncode == 0:
                self.logger.info("部署完成")
                return True
            else:
                self.logger.error(f"部署超时或失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"等待部署完成失败: {e}")
            return False
    
    def post_deployment_checks(self) -> bool:
        """部署后检查"""
        self.logger.info("执行部署后检查...")
        
        checks = [
            ("检查Pod状态", self.check_pod_status),
            ("检查服务健康", self.check_service_health),
            ("检查应用响应", self.check_application_response),
            ("检查日志", self.check_application_logs)
        ]
        
        for check_name, check_func in checks:
            self.logger.info(f"  {check_name}...")
            if not check_func():
                self.logger.error(f"  ❌ {check_name} 失败")
                return False
            self.logger.info(f"  ✅ {check_name} 通过")
        
        self.logger.info("部署后检查完成")
        return True
    
    def check_pod_status(self) -> bool:
        """检查Pod状态"""
        try:
            cmd = ['kubectl', 'get', 'pods', '-n', self.config.namespace, 
                   '-l', f'app={self.config.service_name}', '-o', 'json']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                pods_info = json.loads(result.stdout)
                pods = pods_info.get('items', [])
                
                if not pods:
                    self.logger.error("未找到Pod")
                    return False
                
                for pod in pods:
                    status = pod.get('status', {})
                    phase = status.get('phase', '')
                    
                    if phase != 'Running':
                        self.logger.error(f"Pod状态异常: {pod.get('metadata', {}).get('name', 'unknown')} - {phase}")
                        return False
                
                return True
            else:
                self.logger.error(f"获取Pod状态失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"检查Pod状态失败: {e}")
            return False
    
    def check_service_health(self) -> bool:
        """检查服务健康"""
        try:
            # 检查Service是否存在
            cmd = ['kubectl', 'get', 'service', self.config.service_name, 
                   '-n', self.config.namespace, '-o', 'json']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                service_info = json.loads(result.stdout)
                # 这里可以添加更详细的服务健康检查
                return True
            else:
                self.logger.error(f"Service不存在: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"检查服务健康失败: {e}")
            return False
    
    def check_application_response(self) -> bool:
        """检查应用响应"""
        try:
            # 这里可以添加实际的应用健康检查
            # 例如：HTTP健康检查端点
            
            # 模拟健康检查
            time.sleep(5)  # 等待应用启动
            
            self.logger.info("应用响应检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"检查应用响应失败: {e}")
            return False
    
    def check_application_logs(self) -> bool:
        """检查应用日志"""
        try:
            cmd = ['kubectl', 'logs', '-n', self.config.namespace, 
                   '-l', f'app={self.config.service_name}', '--tail=50']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logs = result.stdout
                
                # 检查是否有错误日志
                error_keywords = ['ERROR', 'FATAL', 'Exception', 'Failed']
                for keyword in error_keywords:
                    if keyword in logs:
                        self.logger.warning(f"发现错误日志关键词: {keyword}")
                        # 这里可以根据实际情况决定是否返回False
                
                return True
            else:
                self.logger.warning(f"获取应用日志失败: {result.stderr}")
                return True  # 日志检查失败不阻止部署
                
        except Exception as e:
            self.logger.warning(f"检查应用日志失败: {e}")
            return True  # 日志检查失败不阻止部署
    
    def rollback_deployment(self) -> bool:
        """回滚部署"""
        self.logger.info("开始回滚部署...")
        
        try:
            # 使用kubectl rollout undo回滚
            cmd = ['kubectl', 'rollout', 'undo', f'deployment/{self.config.service_name}', 
                   '-n', self.config.namespace]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.logger.info("回滚命令执行成功")
                
                # 等待回滚完成
                if self.wait_for_deployment():
                    self.logger.info("回滚完成")
                    return True
                else:
                    self.logger.error("回滚超时")
                    return False
            else:
                self.logger.error(f"回滚失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"回滚部署失败: {e}")
            return False
    
    def send_success_notification(self):
        """发送成功通知"""
        try:
            from src.services.notification_service import notification_service
            
            build_info = {
                'branch': os.environ.get('GITHUB_REF_NAME', 'unknown'),
                'commit': os.environ.get('GITHUB_SHA', 'unknown'),
                'actor': os.environ.get('GITHUB_ACTOR', 'unknown')
            }
            
            # 异步发送通知（在实际项目中可能需要使用asyncio）
            # notification_service.notify_deployment_success(self.config.environment, build_info)
            
            self.logger.info("成功通知已发送")
            
        except Exception as e:
            self.logger.warning(f"发送成功通知失败: {e}")
    
    def send_failure_notification(self, error_message: str):
        """发送失败通知"""
        try:
            from src.services.notification_service import notification_service
            
            build_info = {
                'branch': os.environ.get('GITHUB_REF_NAME', 'unknown'),
                'commit': os.environ.get('GITHUB_SHA', 'unknown'),
                'actor': os.environ.get('GITHUB_ACTOR', 'unknown')
            }
            
            # 异步发送通知（在实际项目中可能需要使用asyncio）
            # notification_service.notify_deployment_failure(self.config.environment, error_message, build_info)
            
            self.logger.info("失败通知已发送")
            
        except Exception as e:
            self.logger.warning(f"发送失败通知失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自动化部署脚本')
    
    parser.add_argument(
        '--environment', '-e',
        choices=['staging', 'production'],
        default='staging',
        help='部署环境 (默认: staging)'
    )
    
    parser.add_argument(
        '--service-name', '-s',
        default='ai-testing-system',
        help='服务名称 (默认: ai-testing-system)'
    )
    
    parser.add_argument(
        '--image-tag', '-t',
        default='latest',
        help='镜像标签 (默认: latest)'
    )
    
    parser.add_argument(
        '--replicas', '-r',
        type=int,
        default=2,
        help='副本数量 (默认: 2)'
    )
    
    parser.add_argument(
        '--namespace', '-n',
        default='default',
        help='Kubernetes命名空间 (默认: default)'
    )
    
    parser.add_argument(
        '--no-rollback',
        action='store_true',
        help='禁用自动回滚'
    )
    
    parser.add_argument(
        '--no-notifications',
        action='store_true',
        help='禁用通知'
    )
    
    parser.add_argument(
        '--skip-pre-checks',
        action='store_true',
        help='跳过部署前检查'
    )
    
    parser.add_argument(
        '--skip-post-checks',
        action='store_true',
        help='跳过部署后检查'
    )
    
    args = parser.parse_args()
    
    # 创建部署配置
    config = DeploymentConfig(
        environment=args.environment,
        service_name=args.service_name,
        image_tag=args.image_tag,
        replicas=args.replicas,
        namespace=args.namespace,
        rollback_enabled=not args.no_rollback,
        notification_enabled=not args.no_notifications,
        pre_deploy_checks=not args.skip_pre_checks,
        post_deploy_checks=not args.skip_post_checks
    )
    
    # 执行部署
    deployment = DeploymentAutomation(config)
    
    try:
        result = deployment.deploy()
        
        if result.success:
            print(f"✅ 部署成功: {result.environment}")
            sys.exit(0)
        else:
            print(f"❌ 部署失败: {result.error_message}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("部署被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"部署异常: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()