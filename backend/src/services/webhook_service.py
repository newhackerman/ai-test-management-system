"""
Webhook服务

本模块实现了Webhook发送功能，支持：
- HTTP POST请求发送
- 重试机制
- 签名验证
- 超时控制
"""
import logging
import asyncio
import hashlib
import hmac
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WebhookConfig:
    """Webhook配置"""
    timeout: int = 30  # 超时时间（秒）
    max_retries: int = 3  # 最大重试次数
    retry_delay: int = 5  # 重试延迟（秒）
    secret_key: Optional[str] = None  # 签名密钥

class WebhookService:
    """Webhook服务"""
    
    def __init__(self, config: WebhookConfig = None):
        self.config = config or WebhookConfig()
    
    async def send_webhook(self, url: str, data: Dict[str, Any],
                          headers: Optional[Dict[str, str]] = None,
                          secret_key: Optional[str] = None,
                          max_retries: Optional[int] = None) -> bool:
        """发送Webhook"""
        try:
            # 1. 准备请求数据
            payload = json.dumps(data, ensure_ascii=False, default=str)
            
            # 2. 准备请求头
            request_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'TestManager-Webhook/1.0',
                'X-Webhook-Timestamp': str(int(datetime.utcnow().timestamp()))
            }
            
            if headers:
                request_headers.update(headers)
            
            # 3. 添加签名
            signature_key = secret_key or self.config.secret_key
            if signature_key:
                signature = self._generate_signature(payload, signature_key)
                request_headers['X-Webhook-Signature'] = signature
            
            # 4. 发送请求（带重试）
            retry_count = max_retries or self.config.max_retries
            
            for attempt in range(retry_count + 1):
                try:
                    success = await self._send_request(url, payload, request_headers)
                    if success:
                        logger.info(f"Webhook发送成功: {url}")
                        return True
                    
                    if attempt < retry_count:
                        logger.warning(f"Webhook发送失败，{self.config.retry_delay}秒后重试 ({attempt + 1}/{retry_count}): {url}")
                        await asyncio.sleep(self.config.retry_delay)
                    
                except Exception as e:
                    logger.error(f"Webhook发送异常 (尝试 {attempt + 1}/{retry_count + 1}): {str(e)}")
                    if attempt < retry_count:
                        await asyncio.sleep(self.config.retry_delay)
            
            logger.error(f"Webhook发送最终失败: {url}")
            return False
            
        except Exception as e:
            logger.error(f"Webhook发送异常: {str(e)}")
            return False
    
    async def send_bulk_webhooks(self, webhooks: List[Dict[str, Any]],
                               batch_size: int = 5) -> Dict[str, Any]:
        """批量发送Webhook"""
        try:
            results = {
                'total': len(webhooks),
                'success': 0,
                'failed': 0,
                'errors': []
            }
            
            # 分批发送
            for i in range(0, len(webhooks), batch_size):
                batch = webhooks[i:i + batch_size]
                
                # 并发发送当前批次
                tasks = []
                for webhook in batch:
                    url = webhook.get('url')
                    data = webhook.get('data', {})
                    headers = webhook.get('headers')
                    secret_key = webhook.get('secret_key')
                    
                    if url:
                        task = self.send_webhook(url, data, headers, secret_key)
                        tasks.append((url, task))
                
                # 等待当前批次完成
                batch_results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
                
                # 统计结果
                for (url, _), result in zip(tasks, batch_results):
                    if isinstance(result, Exception):
                        results['failed'] += 1
                        results['errors'].append(f"{url}: {str(result)}")
                    elif result:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"{url}: 发送失败")
                
                # 批次间延迟
                if i + batch_size < len(webhooks):
                    await asyncio.sleep(1)
            
            logger.info(f"批量Webhook发送完成: 总数{results['total']}, 成功{results['success']}, 失败{results['failed']}")
            return results
            
        except Exception as e:
            logger.error(f"批量发送Webhook异常: {str(e)}")
            return {
                'total': len(webhooks),
                'success': 0,
                'failed': len(webhooks),
                'errors': [str(e)]
            }
    
    async def _send_request(self, url: str, payload: str, 
                          headers: Dict[str, str]) -> bool:
        """发送HTTP请求"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, data=payload, headers=headers) as response:
                    # 检查响应状态
                    if 200 <= response.status < 300:
                        logger.debug(f"Webhook响应成功: {response.status}")
                        return True
                    else:
                        response_text = await response.text()
                        logger.warning(f"Webhook响应失败: {response.status}, {response_text}")
                        return False
                        
        except asyncio.TimeoutError:
            logger.error(f"Webhook请求超时: {url}")
            return False
        except aiohttp.ClientError as e:
            logger.error(f"Webhook客户端错误: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Webhook请求异常: {str(e)}")
            return False
    
    def _generate_signature(self, payload: str, secret_key: str) -> str:
        """生成签名"""
        try:
            signature = hmac.new(
                secret_key.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            return f"sha256={signature}"
        except Exception as e:
            logger.error(f"生成签名失败: {str(e)}")
            return ""
    
    def verify_signature(self, payload: str, signature: str, secret_key: str) -> bool:
        """验证签名"""
        try:
            expected_signature = self._generate_signature(payload, secret_key)
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"验证签名失败: {str(e)}")
            return False
    
    async def test_webhook(self, url: str, secret_key: Optional[str] = None) -> Dict[str, Any]:
        """测试Webhook连接"""
        try:
            test_data = {
                'event': 'webhook_test',
                'message': 'This is a test webhook',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            start_time = datetime.utcnow()
            success = await self.send_webhook(url, test_data, secret_key=secret_key)
            end_time = datetime.utcnow()
            
            response_time = (end_time - start_time).total_seconds()
            
            return {
                'success': success,
                'response_time': response_time,
                'url': url,
                'test_data': test_data,
                'timestamp': start_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"测试Webhook失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'timestamp': datetime.utcnow().isoformat()
            }