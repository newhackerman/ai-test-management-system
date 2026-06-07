"""
验证码工具类
"""
import random
import string
import base64
import io
from typing import Dict, Any
from PIL import Image, ImageDraw, ImageFont
from ..core.redis import redis_service


class CaptchaUtils:
    """验证码工具类"""
    
    # 验证码字符集
    CHAR_SET = string.digits + string.ascii_letters
    
    # 验证码图片尺寸
    WIDTH = 120
    HEIGHT = 40
    
    # 验证码过期时间（秒）
    EXPIRE_TIME = 300  # 5分钟
    
    @classmethod
    async def generate_captcha(cls) -> Dict[str, Any]:
        """
        生成验证码
        
        Returns:
            验证码信息字典
        """
        # 生成随机验证码
        code = ''.join(random.choices(cls.CHAR_SET, k=4))
        
        # 生成唯一key
        key = f"captcha:{''.join(random.choices(string.hexdigits.lower(), k=16))}"
        
        # 创建验证码图片
        image = cls._create_captcha_image(code)
        
        # 将图片转换为Base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # 存储验证码到Redis
        await redis_service.set(
            key,
            code.lower(),  # 存储小写形式，验证时不区分大小写
            expire=cls.EXPIRE_TIME
        )
        
        return {
            "key": key,
            "image": f"data:image/png;base64,{image_base64}",
            "expires_in": cls.EXPIRE_TIME
        }
    
    @classmethod
    async def verify_captcha(cls, key: str, code: str) -> bool:
        """
        验证验证码
        
        Args:
            key: 验证码key
            code: 验证码
            
        Returns:
            验证结果
        """
        if not key or not code:
            return False
        
        # 从Redis获取验证码
        stored_code = await redis_service.get(key)
        if not stored_code:
            return False
        
        # 验证码不区分大小写
        return stored_code == code.lower()
    
    @classmethod
    def _create_captcha_image(cls, code: str) -> Image.Image:
        """
        创建验证码图片
        
        Args:
            code: 验证码
            
        Returns:
            验证码图片
        """
        # 创建空白图片
        image = Image.new('RGB', (cls.WIDTH, cls.HEIGHT), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # 尝试加载字体，如果失败则使用默认字体
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            try:
                # 尝试使用系统中其他字体
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except:
                # 使用默认字体
                font = ImageFont.load_default()
        
        # 绘制验证码字符
        for i, char in enumerate(code):
            # 随机字符位置
            x = 10 + i * 25 + random.randint(-5, 5)
            y = 5 + random.randint(-5, 5)
            
            # 随机字符颜色
            color = (
                random.randint(0, 100),
                random.randint(0, 100),
                random.randint(0, 100)
            )
            
            # 绘制字符
            draw.text((x, y), char, fill=color, font=font)
        
        # 添加干扰线
        for _ in range(random.randint(3, 5)):
            # 随机线条起点和终点
            x1 = random.randint(0, cls.WIDTH)
            y1 = random.randint(0, cls.HEIGHT)
            x2 = random.randint(0, cls.WIDTH)
            y2 = random.randint(0, cls.HEIGHT)
            
            # 随机线条颜色
            color = (
                random.randint(0, 200),
                random.randint(0, 200),
                random.randint(0, 200)
            )
            
            # 绘制线条
            draw.line([(x1, y1), (x2, y2)], fill=color, width=1)
        
        # 添加干扰点
        for _ in range(random.randint(30, 50)):
            # 随机点位置
            x = random.randint(0, cls.WIDTH)
            y = random.randint(0, cls.HEIGHT)
            
            # 随机点颜色
            color = (
                random.randint(0, 200),
                random.randint(0, 200),
                random.randint(0, 200)
            )
            
            # 绘制点
            draw.point((x, y), fill=color)
        
        return image