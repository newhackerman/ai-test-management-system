"""
通知服务模块

提供多渠道通知功能，支持邮件、Slack、企业微信等通知方式
"""
import os
import json
import logging
import smtplib
import requests
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class NotificationConfig:
    """通知配置"""
    # 邮件配置
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: List[str] = None
    
    # Slack配置
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    
    # 企业微信配置
    wechat_webhook_url: Optional[str] = None
    
    # 钉钉配置
    dingtalk_webhook_url: Optional[str] = None
    dingtalk_secret: Optional[str] = None
    
    def __post_init__(self):
        if self.email_to is None:
            self.email_to = []

@dataclass
class NotificationMessage:
    """通知消息"""
    title: str
    content: str
    message_type: str = 'info'  # info, success, warning, error
    attachments: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []
        if self.metadata is None:
            self.metadata = {}

class NotificationService:
    """通知服务"""
    
    def __init__(self, config: NotificationConfig = None):
        self.config = config or self._load_config_from_env()
        self.logger = logging.getLogger(__name__)
    
    def _load_config_from_env(self) -> NotificationConfig:
        """从环境变量加载配置"""
        return NotificationConfig(
            smtp_server=os.environ.get('SMTP_SERVER'),
            smtp_port=int(os.environ.get('SMTP_PORT', 587)),
            smtp_username=os.environ.get('SMTP_USERNAME'),
            smtp_password=os.environ.get('SMTP_PASSWORD'),
            email_from=os.environ.get('EMAIL_FROM'),
            email_to=os.environ.get('EMAIL_TO', '').split(',') if os.environ.get('EMAIL_TO') else [],
            slack_webhook_url=os.environ.get('SLACK_WEBHOOK_URL'),
            slack_channel=os.environ.get('SLACK_CHANNEL'),
            wechat_webhook_url=os.environ.get('WECHAT_WEBHOOK_URL'),
            dingtalk_webhook_url=os.environ.get('DINGTALK_WEBHOOK_URL'),
            dingtalk_secret=os.environ.get('DINGTALK_SECRET')
        )
    
    async def send_notification(self, message: NotificationMessage, 
                              channels: List[str] = None) -> Dict[str, bool]:
        """发送通知到指定渠道"""
        if channels is None:
            channels = ['email', 'slack', 'wechat', 'dingtalk']
        
        results = {}
        
        for channel in channels:
            try:
                if channel == 'email' and self._is_email_configured():
                    results['email'] = await self._send_email(message)
                elif channel == 'slack' and self._is_slack_configured():
                    results['slack'] = await self._send_slack(message)
                elif channel == 'wechat' and self._is_wechat_configured():
                    results['wechat'] = await self._send_wechat(message)
                elif channel == 'dingtalk' and self._is_dingtalk_configured():
                    results['dingtalk'] = await self._send_dingtalk(message)
                else:
                    self.logger.debug(f"跳过未配置的通知渠道: {channel}")
                    
            except Exception as e:
                self.logger.error(f"发送 {channel} 通知失败: {e}")
                results[channel] = False
        
        return results
    
    def _is_email_configured(self) -> bool:
        """检查邮件是否配置"""
        return bool(
            self.config.smtp_server and 
            self.config.smtp_username and 
            self.config.smtp_password and
            self.config.email_to
        )
    
    def _is_slack_configured(self) -> bool:
        """检查Slack是否配置"""
        return bool(self.config.slack_webhook_url)
    
    def _is_wechat_configured(self) -> bool:
        """检查企业微信是否配置"""
        return bool(self.config.wechat_webhook_url)
    
    def _is_dingtalk_configured(self) -> bool:
        """检查钉钉是否配置"""
        return bool(self.config.dingtalk_webhook_url)
    
    async def _send_email(self, message: NotificationMessage) -> bool:
        """发送邮件通知"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.email_from or self.config.smtp_username
            msg['To'] = ', '.join(self.config.email_to)
            msg['Subject'] = message.title
            
            # 添加邮件正文
            body = self._format_email_body(message)
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # 添加附件
            for attachment_path in message.attachments:
                if os.path.exists(attachment_path):
                    with open(attachment_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(attachment_path)}'
                        )
                        msg.attach(part)
            
            # 发送邮件
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            server.starttls()
            server.login(self.config.smtp_username, self.config.smtp_password)
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"邮件通知发送成功: {message.title}")
            return True
            
        except Exception as e:
            self.logger.error(f"发送邮件失败: {e}")
            return False
    
    def _format_email_body(self, message: NotificationMessage) -> str:
        """格式化邮件正文"""
        # 根据消息类型选择颜色
        color_map = {
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        }
        
        color = color_map.get(message.message_type, '#17a2b8')
        icon_map = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        
        icon = icon_map.get(message.message_type, 'ℹ️')
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: {color}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; line-height: 1.6; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; color: #6c757d; font-size: 12px; }}
                .metadata {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 4px; }}
                .metadata h4 {{ margin: 0 0 10px 0; color: #495057; }}
                .metadata table {{ width: 100%; border-collapse: collapse; }}
                .metadata td {{ padding: 5px 0; border-bottom: 1px solid #dee2e6; }}
                .metadata td:first-child {{ font-weight: bold; width: 30%; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{icon} {message.title}</h1>
                </div>
                <div class="content">
                    {message.content.replace(chr(10), '<br>')}
                    
                    {self._format_metadata_html(message.metadata) if message.metadata else ''}
                </div>
                <div class="footer">
                    <p>此邮件由 AI 自动化测试管理系统自动发送</p>
                    <p>发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _format_metadata_html(self, metadata: Dict[str, Any]) -> str:
        """格式化元数据为HTML"""
        if not metadata:
            return ""
        
        rows = ""
        for key, value in metadata.items():
            rows += f"<tr><td>{key}</td><td>{value}</td></tr>"
        
        return f"""
        <div class="metadata">
            <h4>详细信息</h4>
            <table>
                {rows}
            </table>
        </div>
        """
    
    async def _send_slack(self, message: NotificationMessage) -> bool:
        """发送Slack通知"""
        try:
            # 根据消息类型选择颜色
            color_map = {
                'success': 'good',
                'error': 'danger',
                'warning': 'warning',
                'info': '#17a2b8'
            }
            
            color = color_map.get(message.message_type, '#17a2b8')
            
            # 构建Slack消息
            slack_message = {
                "text": message.title,
                "attachments": [
                    {
                        "color": color,
                        "title": message.title,
                        "text": message.content,
                        "footer": "AI 自动化测试管理系统",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            # 添加元数据字段
            if message.metadata:
                fields = []
                for key, value in message.metadata.items():
                    fields.append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })
                slack_message["attachments"][0]["fields"] = fields
            
            # 发送到Slack
            response = requests.post(
                self.config.slack_webhook_url,
                json=slack_message,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"Slack通知发送成功: {message.title}")
                return True
            else:
                self.logger.error(f"Slack通知发送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"发送Slack通知失败: {e}")
            return False
    
    async def _send_wechat(self, message: NotificationMessage) -> bool:
        """发送企业微信通知"""
        try:
            # 构建企业微信消息
            wechat_message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"## {message.title}\n\n{message.content}"
                }
            }
            
            # 添加元数据
            if message.metadata:
                wechat_message["markdown"]["content"] += "\n\n**详细信息:**\n"
                for key, value in message.metadata.items():
                    wechat_message["markdown"]["content"] += f"- **{key}**: {value}\n"
            
            # 发送到企业微信
            response = requests.post(
                self.config.wechat_webhook_url,
                json=wechat_message,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    self.logger.info(f"企业微信通知发送成功: {message.title}")
                    return True
                else:
                    self.logger.error(f"企业微信通知发送失败: {result}")
                    return False
            else:
                self.logger.error(f"企业微信通知发送失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"发送企业微信通知失败: {e}")
            return False
    
    async def _send_dingtalk(self, message: NotificationMessage) -> bool:
        """发送钉钉通知"""
        try:
            # 构建钉钉消息
            dingtalk_message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": message.title,
                    "text": f"## {message.title}\n\n{message.content}"
                }
            }
            
            # 添加元数据
            if message.metadata:
                dingtalk_message["markdown"]["text"] += "\n\n**详细信息:**\n"
                for key, value in message.metadata.items():
                    dingtalk_message["markdown"]["text"] += f"- **{key}**: {value}\n"
            
            # 如果配置了签名，添加签名
            url = self.config.dingtalk_webhook_url
            if self.config.dingtalk_secret:
                import time
                import hmac
                import hashlib
                import base64
                import urllib.parse
                
                timestamp = str(round(time.time() * 1000))
                secret_enc = self.config.dingtalk_secret.encode('utf-8')
                string_to_sign = f'{timestamp}\n{self.config.dingtalk_secret}'
                string_to_sign_enc = string_to_sign.encode('utf-8')
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                url = f"{url}&timestamp={timestamp}&sign={sign}"
            
            # 发送到钉钉
            response = requests.post(
                url,
                json=dingtalk_message,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    self.logger.info(f"钉钉通知发送成功: {message.title}")
                    return True
                else:
                    self.logger.error(f"钉钉通知发送失败: {result}")
                    return False
            else:
                self.logger.error(f"钉钉通知发送失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"发送钉钉通知失败: {e}")
            return False

class CINotificationService(NotificationService):
    """CI/CD专用通知服务"""
    
    def __init__(self):
        super().__init__()
    
    async def notify_test_success(self, test_results: Dict[str, Any], 
                                 build_info: Dict[str, str] = None) -> Dict[str, bool]:
        """通知测试成功"""
        build_info = build_info or {}
        
        # 构建成功消息
        summary = test_results.get('summary', {})
        
        title = f"✅ CI/CD 测试执行成功 - {build_info.get('branch', 'unknown')}"
        
        content = f"""
测试执行成功完成！

**执行信息:**
- 分支: {build_info.get('branch', 'unknown')}
- 提交: {build_info.get('commit', 'unknown')}
- 执行者: {build_info.get('actor', 'unknown')}

**测试结果:**
- 总测试数: {summary.get('total_tests', 0)}
- 通过: {summary.get('passed', 0)}
- 失败: {summary.get('failed', 0)}
- 跳过: {summary.get('skipped', 0)}
- 成功率: {summary.get('success_rate', 0):.1f}%
- 执行时长: {summary.get('total_duration', 0):.2f}s

所有测试套件执行成功，系统运行正常。
        """
        
        metadata = {
            "分支": build_info.get('branch', 'unknown'),
            "提交": build_info.get('commit', 'unknown'),
            "执行者": build_info.get('actor', 'unknown'),
            "总测试数": summary.get('total_tests', 0),
            "成功率": f"{summary.get('success_rate', 0):.1f}%",
            "执行时长": f"{summary.get('total_duration', 0):.2f}s"
        }
        
        message = NotificationMessage(
            title=title,
            content=content,
            message_type='success',
            metadata=metadata
        )
        
        return await self.send_notification(message)
    
    async def notify_test_failure(self, test_results: Dict[str, Any], 
                                 build_info: Dict[str, str] = None,
                                 failed_suites: List[str] = None) -> Dict[str, bool]:
        """通知测试失败"""
        build_info = build_info or {}
        failed_suites = failed_suites or []
        
        # 构建失败消息
        summary = test_results.get('summary', {})
        
        title = f"❌ CI/CD 测试执行失败 - {build_info.get('branch', 'unknown')}"
        
        content = f"""
测试执行失败，请及时处理！

**执行信息:**
- 分支: {build_info.get('branch', 'unknown')}
- 提交: {build_info.get('commit', 'unknown')}
- 执行者: {build_info.get('actor', 'unknown')}

**失败详情:**
- 失败的测试套件: {', '.join(failed_suites) if failed_suites else '未知'}
- 总测试数: {summary.get('total_tests', 0)}
- 通过: {summary.get('passed', 0)}
- 失败: {summary.get('failed', 0)}
- 错误: {summary.get('errors', 0)}
- 成功率: {summary.get('success_rate', 0):.1f}%

**处理建议:**
1. 检查失败的测试用例
2. 修复代码质量问题
3. 确保所有依赖正常
4. 重新提交修复

请查看详细日志并及时修复问题。
        """
        
        metadata = {
            "分支": build_info.get('branch', 'unknown'),
            "提交": build_info.get('commit', 'unknown'),
            "执行者": build_info.get('actor', 'unknown'),
            "失败套件": ', '.join(failed_suites) if failed_suites else '未知',
            "总测试数": summary.get('total_tests', 0),
            "失败数": summary.get('failed', 0),
            "成功率": f"{summary.get('success_rate', 0):.1f}%"
        }
        
        message = NotificationMessage(
            title=title,
            content=content,
            message_type='error',
            metadata=metadata
        )
        
        return await self.send_notification(message)
    
    async def notify_deployment_success(self, environment: str, 
                                      build_info: Dict[str, str] = None) -> Dict[str, bool]:
        """通知部署成功"""
        build_info = build_info or {}
        
        title = f"🚀 {environment.upper()} 环境部署成功"
        
        content = f"""
{environment.upper()} 环境部署成功！

**部署信息:**
- 环境: {environment.upper()}
- 分支: {build_info.get('branch', 'unknown')}
- 提交: {build_info.get('commit', 'unknown')}
- 部署者: {build_info.get('actor', 'unknown')}
- 部署时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

系统已成功上线运行。
        """
        
        metadata = {
            "环境": environment.upper(),
            "分支": build_info.get('branch', 'unknown'),
            "提交": build_info.get('commit', 'unknown'),
            "部署者": build_info.get('actor', 'unknown'),
            "部署时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        message = NotificationMessage(
            title=title,
            content=content,
            message_type='success',
            metadata=metadata
        )
        
        return await self.send_notification(message)
    
    async def notify_deployment_failure(self, environment: str, 
                                      error_message: str = None,
                                      build_info: Dict[str, str] = None) -> Dict[str, bool]:
        """通知部署失败"""
        build_info = build_info or {}
        
        title = f"🚨 {environment.upper()} 环境部署失败"
        
        content = f"""
{environment.upper()} 环境部署失败，请及时处理！

**部署信息:**
- 环境: {environment.upper()}
- 分支: {build_info.get('branch', 'unknown')}
- 提交: {build_info.get('commit', 'unknown')}
- 部署者: {build_info.get('actor', 'unknown')}
- 失败时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**错误信息:**
{error_message or '未知错误'}

请检查部署日志并及时修复问题。
        """
        
        metadata = {
            "环境": environment.upper(),
            "分支": build_info.get('branch', 'unknown'),
            "提交": build_info.get('commit', 'unknown'),
            "部署者": build_info.get('actor', 'unknown'),
            "失败时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "错误信息": error_message or '未知错误'
        }
        
        message = NotificationMessage(
            title=title,
            content=content,
            message_type='error',
            metadata=metadata
        )
        
        return await self.send_notification(message)


# 全局通知服务实例
notification_service = CINotificationService()