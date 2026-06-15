"""
邮件服务

本模块实现了邮件发送功能，支持：
- HTML和纯文本邮件
- 附件发送
- 邮件模板
- 批量发送
"""
import logging
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EmailConfig:
    """邮件配置"""
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    use_tls: bool = True
    use_ssl: bool = False
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    timeout: int = 10

class EmailService:
    """邮件服务"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.from_email = config.from_email or config.username
        self.from_name = config.from_name or "测试管理系统"
    
    async def send_email(self, to: List[str], subject: str, body: str,
                        cc: Optional[List[str]] = None,
                        bcc: Optional[List[str]] = None,
                        is_html: bool = False,
                        attachments: Optional[List[str]] = None,
                        reply_to: Optional[str] = None) -> bool:
        """发送邮件"""
        try:
            # 1. 创建邮件消息
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = ', '.join(to)
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # 2. 添加邮件正文
            if is_html:
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 3. 添加附件
            if attachments:
                for attachment_path in attachments:
                    if await self._add_attachment(msg, attachment_path):
                        logger.debug(f"附件添加成功: {attachment_path}")
                    else:
                        logger.warning(f"附件添加失败: {attachment_path}")
            
            # 4. 发送邮件
            success = await self._send_message(msg, to, cc, bcc)
            
            if success:
                logger.info(f"邮件发送成功: {subject} -> {', '.join(to)}")
            else:
                logger.error(f"邮件发送失败: {subject} -> {', '.join(to)}")
            
            return success
            
        except Exception as e:
            logger.error(f"发送邮件异常: {str(e)}")
            return False
    
    async def send_template_email(self, to: List[str], template_name: str,
                                template_data: Dict[str, Any],
                                cc: Optional[List[str]] = None,
                                bcc: Optional[List[str]] = None,
                                attachments: Optional[List[str]] = None) -> bool:
        """发送模板邮件"""
        try:
            # 1. 加载邮件模板
            template = await self._load_email_template(template_name)
            if not template:
                logger.error(f"邮件模板不存在: {template_name}")
                return False
            
            # 2. 渲染模板
            subject = self._render_template(template.get('subject', ''), template_data)
            body = self._render_template(template.get('body', ''), template_data)
            
            # 3. 发送邮件
            return await self.send_email(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                is_html=template.get('is_html', True),
                attachments=attachments
            )
            
        except Exception as e:
            logger.error(f"发送模板邮件异常: {str(e)}")
            return False
    
    async def send_bulk_email(self, recipients: List[Dict[str, Any]], 
                            subject: str, body: str,
                            is_html: bool = False,
                            batch_size: int = 10) -> Dict[str, Any]:
        """批量发送邮件"""
        try:
            results = {
                'total': len(recipients),
                'success': 0,
                'failed': 0,
                'errors': []
            }
            
            # 分批发送
            for i in range(0, len(recipients), batch_size):
                batch = recipients[i:i + batch_size]
                
                # 并发发送当前批次
                tasks = []
                for recipient in batch:
                    email = recipient.get('email')
                    if email:
                        # 个性化内容
                        personalized_body = self._render_template(body, recipient)
                        personalized_subject = self._render_template(subject, recipient)
                        
                        task = self.send_email(
                            to=[email],
                            subject=personalized_subject,
                            body=personalized_body,
                            is_html=is_html
                        )
                        tasks.append((email, task))
                
                # 等待当前批次完成
                batch_results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
                
                # 统计结果
                for (email, _), result in zip(tasks, batch_results):
                    if isinstance(result, Exception):
                        results['failed'] += 1
                        results['errors'].append(f"{email}: {str(result)}")
                    elif result:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"{email}: 发送失败")
                
                # 批次间延迟，避免过于频繁
                if i + batch_size < len(recipients):
                    await asyncio.sleep(1)
            
            logger.info(f"批量邮件发送完成: 总数{results['total']}, 成功{results['success']}, 失败{results['failed']}")
            return results
            
        except Exception as e:
            logger.error(f"批量发送邮件异常: {str(e)}")
            return {
                'total': len(recipients),
                'success': 0,
                'failed': len(recipients),
                'errors': [str(e)]
            }
    
    async def _send_message(self, msg: MIMEMultipart, to: List[str],
                          cc: Optional[List[str]] = None,
                          bcc: Optional[List[str]] = None) -> bool:
        """发送邮件消息"""
        try:
            # 构建收件人列表
            recipients = to.copy()
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # 在异步环境中运行同步的SMTP操作
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._send_message_sync, msg, recipients
            )
            
        except Exception as e:
            logger.error(f"发送邮件消息失败: {str(e)}")
            return False
    
    def _send_message_sync(self, msg: MIMEMultipart, recipients: List[str]) -> bool:
        """同步发送邮件消息"""
        try:
            # 创建SMTP连接
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port, timeout=self.config.timeout)
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=self.config.timeout)
                if self.config.use_tls:
                    server.starttls()
            
            # 登录
            server.login(self.config.username, self.config.password)
            
            # 发送邮件
            text = msg.as_string()
            server.sendmail(self.from_email, recipients, text)
            
            # 关闭连接
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"同步发送邮件失败: {str(e)}")
            return False
    
    async def _add_attachment(self, msg: MIMEMultipart, file_path: str) -> bool:
        """添加附件"""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"附件文件不存在: {file_path}")
                return False
            
            # 读取文件
            with open(path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            # 编码附件
            encoders.encode_base64(part)
            
            # 添加头信息
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {path.name}',
            )
            
            # 添加到邮件
            msg.attach(part)
            
            return True
            
        except Exception as e:
            logger.error(f"添加附件失败: {str(e)}")
            return False
    
    async def _load_email_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """加载邮件模板"""
        try:
            # 简化实现，实际应该从数据库或文件系统加载
            templates = {
                'report_notification': {
                    'subject': '测试报告通知: {report_name}',
                    'body': '''
                    <h3>测试报告通知</h3>
                    <p>尊敬的 {recipient_name}，</p>
                    <p>新的测试报告已生成：</p>
                    <ul>
                        <li><strong>报告名称:</strong> {report_name}</li>
                        <li><strong>报告类型:</strong> {report_type}</li>
                        <li><strong>生成时间:</strong> {created_at}</li>
                        <li><strong>项目:</strong> {project_name}</li>
                    </ul>
                    <p>请点击以下链接查看报告详情：</p>
                    <p><a href="{report_url}">查看报告</a></p>
                    <p>此致<br>测试管理系统</p>
                    ''',
                    'is_html': True
                },
                'subscription_confirmation': {
                    'subject': '报告订阅确认: {subscription_name}',
                    'body': '''
                    <h3>报告订阅确认</h3>
                    <p>尊敬的 {user_name}，</p>
                    <p>您的报告订阅已成功创建：</p>
                    <ul>
                        <li><strong>订阅名称:</strong> {subscription_name}</li>
                        <li><strong>订阅类型:</strong> {subscription_type}</li>
                        <li><strong>分发渠道:</strong> {delivery_channels}</li>
                        <li><strong>创建时间:</strong> {created_at}</li>
                    </ul>
                    <p>您将根据订阅设置接收相关报告通知。</p>
                    <p>如需修改或取消订阅，请登录系统进行操作。</p>
                    <p>此致<br>测试管理系统</p>
                    ''',
                    'is_html': True
                }
            }
            
            return templates.get(template_name)
            
        except Exception as e:
            logger.error(f"加载邮件模板失败: {str(e)}")
            return None
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """渲染模板"""
        try:
            return template.format(**data)
        except KeyError as e:
            logger.warning(f"模板变量缺失: {e}")
            return template
        except Exception as e:
            logger.error(f"渲染模板失败: {str(e)}")
            return template
    
    def test_connection(self) -> bool:
        """测试邮件服务连接"""
        try:
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port, timeout=self.config.timeout)
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=self.config.timeout)
                if self.config.use_tls:
                    server.starttls()
            
            server.login(self.config.username, self.config.password)
            server.quit()
            
            logger.info("邮件服务连接测试成功")
            return True
            
        except Exception as e:
            logger.error(f"邮件服务连接测试失败: {str(e)}")
            return False
