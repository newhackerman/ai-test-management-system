"""
AI流式响应处理工具

提供流式响应的核心处理功能，包括：
1. 流式数据处理和缓冲
2. 打字机效果实现
3. 流式响应优化
4. 错误处理和恢复
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, AsyncGenerator, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..adapters.base import StreamChunk, AIProvider

logger = logging.getLogger(__name__)


class StreamProcessingMode(Enum):
    """流处理模式"""
    REAL_TIME = "real_time"  # 实时模式，立即传输
    BUFFERED = "buffered"    # 缓冲模式，批量传输
    OPTIMIZED = "optimized"  # 优化模式，智能缓冲


@dataclass
class StreamBuffer:
    """流缓冲区"""
    content: str = ""
    chunk_count: int = 0
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    buffer_size: int = 0
    
    def add_chunk(self, chunk: StreamChunk):
        """添加数据块到缓冲区"""
        self.content += chunk.content
        self.chunk_count += 1
        self.buffer_size = len(self.content)
        self.last_update = datetime.now(timezone.utc)
    
    def clear(self):
        """清空缓冲区"""
        self.content = ""
        self.chunk_count = 0
        self.buffer_size = 0
        self.last_update = datetime.now(timezone.utc)
    
    def get_content(self) -> str:
        """获取缓冲区内容"""
        return self.content


@dataclass
class StreamMetrics:
    """流式响应性能指标"""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    total_chunks: int = 0
    total_bytes: int = 0
    processing_time: float = 0.0
    transmission_time: float = 0.0
    error_count: int = 0
    
    def add_chunk(self, chunk: StreamChunk):
        """记录数据块指标"""
        self.total_chunks += 1
        self.total_bytes += len(chunk.content.encode('utf-8'))
    
    def mark_complete(self):
        """标记完成"""
        self.end_time = datetime.now(timezone.utc)
        if self.start_time:
            self.processing_time = (self.end_time - self.start_time).total_seconds()
    
    def get_throughput(self) -> float:
        """获取吞吐量 (字节/秒)"""
        if self.processing_time > 0:
            return self.total_bytes / self.processing_time
        return 0.0
    
    def get_chunk_rate(self) -> float:
        """获取数据块速率 (块/秒)"""
        if self.processing_time > 0:
            return self.total_chunks / self.processing_time
        return 0.0


class StreamProcessor:
    """流式响应处理器"""
    
    def __init__(self, 
                 mode: StreamProcessingMode = StreamProcessingMode.OPTIMIZED,
                 buffer_size: int = 1024,
                 flush_interval: float = 0.1,
                 typing_speed: float = 50.0):
        """
        初始化流处理器
        
        Args:
            mode: 处理模式
            buffer_size: 缓冲区大小 (字符数)
            flush_interval: 刷新间隔 (秒)
            typing_speed: 打字机速度 (字符/秒)
        """
        self.mode = mode
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.typing_speed = typing_speed
        
        self.buffer = StreamBuffer()
        self.metrics = StreamMetrics()
        
        # 处理状态
        self.is_processing = False
        self.is_paused = False
        self.should_stop = False
        
        # 回调函数
        self.on_chunk_processed: Optional[Callable[[StreamChunk], None]] = None
        self.on_buffer_flushed: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        logger.info(f"StreamProcessor initialized with mode: {mode.value}")
    
    async def process_stream(self, 
                           stream: AsyncGenerator[StreamChunk, None],
                           output_callback: Callable[[str], None]) -> StreamMetrics:
        """
        处理流式响应
        
        Args:
            stream: 流式数据生成器
            output_callback: 输出回调函数
            
        Returns:
            StreamMetrics: 处理指标
        """
        self.is_processing = True
        self.should_stop = False
        self.metrics = StreamMetrics()
        
        try:
            if self.mode == StreamProcessingMode.REAL_TIME:
                await self._process_real_time(stream, output_callback)
            elif self.mode == StreamProcessingMode.BUFFERED:
                await self._process_buffered(stream, output_callback)
            else:  # OPTIMIZED
                await self._process_optimized(stream, output_callback)
                
        except Exception as e:
            logger.error(f"Stream processing error: {e}")
            if self.on_error:
                self.on_error(e)
            raise
        finally:
            self.is_processing = False
            self.metrics.mark_complete()
        
        return self.metrics
    
    async def _process_real_time(self, 
                               stream: AsyncGenerator[StreamChunk, None],
                               output_callback: Callable[[str], None]):
        """实时处理模式"""
        async for chunk in stream:
            if self.should_stop:
                break
                
            while self.is_paused:
                await asyncio.sleep(0.1)
            
            # 立即输出
            output_callback(chunk.content)
            
            # 更新指标
            self.metrics.add_chunk(chunk)
            
            # 调用回调
            if self.on_chunk_processed:
                self.on_chunk_processed(chunk)
            
            if chunk.is_final:
                break
    
    async def _process_buffered(self, 
                              stream: AsyncGenerator[StreamChunk, None],
                              output_callback: Callable[[str], None]):
        """缓冲处理模式"""
        async for chunk in stream:
            if self.should_stop:
                break
                
            while self.is_paused:
                await asyncio.sleep(0.1)
            
            # 添加到缓冲区
            self.buffer.add_chunk(chunk)
            self.metrics.add_chunk(chunk)
            
            # 检查是否需要刷新缓冲区
            should_flush = (
                self.buffer.buffer_size >= self.buffer_size or
                chunk.is_final or
                (datetime.now(timezone.utc) - self.buffer.last_update).total_seconds() >= self.flush_interval
            )
            
            if should_flush:
                content = self.buffer.get_content()
                output_callback(content)
                
                if self.on_buffer_flushed:
                    self.on_buffer_flushed(content)
                
                self.buffer.clear()
            
            # 调用回调
            if self.on_chunk_processed:
                self.on_chunk_processed(chunk)
            
            if chunk.is_final:
                break
    
    async def _process_optimized(self, 
                               stream: AsyncGenerator[StreamChunk, None],
                               output_callback: Callable[[str], None]):
        """优化处理模式"""
        chunk_times = []
        adaptive_buffer_size = self.buffer_size
        
        async for chunk in stream:
            if self.should_stop:
                break
                
            while self.is_paused:
                await asyncio.sleep(0.1)
            
            chunk_start_time = time.time()
            
            # 添加到缓冲区
            self.buffer.add_chunk(chunk)
            self.metrics.add_chunk(chunk)
            
            # 记录处理时间
            chunk_times.append(time.time() - chunk_start_time)
            
            # 动态调整缓冲区大小
            if len(chunk_times) >= 10:
                avg_chunk_time = sum(chunk_times[-10:]) / 10
                if avg_chunk_time > 0.05:  # 如果处理较慢，增加缓冲
                    adaptive_buffer_size = min(adaptive_buffer_size * 1.2, self.buffer_size * 2)
                elif avg_chunk_time < 0.01:  # 如果处理很快，减少缓冲
                    adaptive_buffer_size = max(adaptive_buffer_size * 0.8, self.buffer_size * 0.5)
            
            # 智能刷新策略
            should_flush = (
                self.buffer.buffer_size >= adaptive_buffer_size or
                chunk.is_final or
                self._should_flush_smart()
            )
            
            if should_flush:
                content = self.buffer.get_content()
                
                # 应用打字机效果
                if self.typing_speed > 0 and not chunk.is_final:
                    await self._apply_typing_effect(content, output_callback)
                else:
                    output_callback(content)
                
                if self.on_buffer_flushed:
                    self.on_buffer_flushed(content)
                
                self.buffer.clear()
            
            # 调用回调
            if self.on_chunk_processed:
                self.on_chunk_processed(chunk)
            
            if chunk.is_final:
                break
    
    def _should_flush_smart(self) -> bool:
        """智能刷新判断"""
        # 基于时间的刷新
        time_since_last = (datetime.now(timezone.utc) - self.buffer.last_update).total_seconds()
        if time_since_last >= self.flush_interval:
            return True
        
        # 基于内容的刷新（句子结束、段落结束等）
        content = self.buffer.content
        if content.endswith(('.', '!', '?', '\n', '。', '！', '？')):
            return True
        
        # 基于代码块的刷新
        if '```' in content and content.count('```') % 2 == 0:
            return True
        
        return False
    
    async def _apply_typing_effect(self, content: str, output_callback: Callable[[str], None]):
        """应用打字机效果"""
        if not content:
            return
        
        chars_per_interval = max(1, int(self.typing_speed * 0.05))  # 每50ms的字符数
        
        for i in range(0, len(content), chars_per_interval):
            if self.should_stop:
                break
                
            while self.is_paused:
                await asyncio.sleep(0.1)
            
            chunk_text = content[i:i + chars_per_interval]
            output_callback(chunk_text)
            
            # 控制打字速度
            await asyncio.sleep(0.05)
    
    def pause(self):
        """暂停处理"""
        self.is_paused = True
        logger.info("Stream processing paused")
    
    def resume(self):
        """恢复处理"""
        self.is_paused = False
        logger.info("Stream processing resumed")
    
    def stop(self):
        """停止处理"""
        self.should_stop = True
        logger.info("Stream processing stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """获取处理状态"""
        return {
            "is_processing": self.is_processing,
            "is_paused": self.is_paused,
            "should_stop": self.should_stop,
            "mode": self.mode.value,
            "buffer_size": self.buffer.buffer_size,
            "chunk_count": self.buffer.chunk_count,
            "metrics": {
                "total_chunks": self.metrics.total_chunks,
                "total_bytes": self.metrics.total_bytes,
                "throughput": self.metrics.get_throughput(),
                "chunk_rate": self.metrics.get_chunk_rate(),
                "processing_time": self.metrics.processing_time
            }
        }


class StreamOptimizer:
    """流式响应优化器"""
    
    def __init__(self):
        self.compression_enabled = True
        self.deduplication_enabled = True
        self.content_filtering_enabled = True
        
    async def optimize_chunk(self, chunk: StreamChunk) -> StreamChunk:
        """优化数据块"""
        optimized_content = chunk.content
        
        # 内容去重
        if self.deduplication_enabled:
            optimized_content = self._deduplicate_content(optimized_content)
        
        # 内容过滤
        if self.content_filtering_enabled:
            optimized_content = self._filter_content(optimized_content)
        
        # 内容压缩（对于重复模式）
        if self.compression_enabled:
            optimized_content = self._compress_patterns(optimized_content)
        
        # 创建优化后的数据块
        if optimized_content != chunk.content:
            return StreamChunk(
                request_id=chunk.request_id,
                provider=chunk.provider,
                content=optimized_content,
                is_final=chunk.is_final,
                chunk_index=chunk.chunk_index,
                metadata={**chunk.metadata, "optimized": True},
                timestamp=chunk.timestamp
            )
        
        return chunk
    
    def _deduplicate_content(self, content: str) -> str:
        """去除重复内容"""
        # 简单的重复检测和去除
        lines = content.split('\n')
        unique_lines = []
        seen = set()
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped not in seen or len(line_stripped) < 10:
                unique_lines.append(line)
                seen.add(line_stripped)
        
        return '\n'.join(unique_lines)
    
    def _filter_content(self, content: str) -> str:
        """过滤不当内容"""
        # 这里可以添加内容过滤逻辑
        # 例如：移除特殊字符、过滤敏感词等
        
        # 移除控制字符
        filtered = ''.join(char for char in content if ord(char) >= 32 or char in '\n\t')
        
        return filtered
    
    def _compress_patterns(self, content: str) -> str:
        """压缩重复模式"""
        # 检测和压缩重复的模式
        # 这里实现简单的重复模式检测
        
        import re
        
        # 检测重复的单词或短语
        pattern = r'(\b\w+\b)(\s+\1){2,}'
        
        def replace_repetition(match):
            word = match.group(1)
            count = len(match.group(0).split())
            return f"{word} (重复{count}次)"
        
        compressed = re.sub(pattern, replace_repetition, content)
        
        return compressed


class StreamAnalyzer:
    """流式响应分析器"""
    
    def __init__(self):
        self.content_patterns = []
        self.performance_history = []
        
    async def analyze_stream(self, chunks: List[StreamChunk]) -> Dict[str, Any]:
        """分析流式响应"""
        if not chunks:
            return {}
        
        analysis = {
            "total_chunks": len(chunks),
            "total_content_length": sum(len(chunk.content) for chunk in chunks),
            "average_chunk_size": 0,
            "content_type": self._detect_content_type(chunks),
            "language": self._detect_language(chunks),
            "quality_score": self._calculate_quality_score(chunks),
            "patterns": self._detect_patterns(chunks),
            "performance": self._analyze_performance(chunks)
        }
        
        if chunks:
            analysis["average_chunk_size"] = analysis["total_content_length"] / len(chunks)
        
        return analysis
    
    def _detect_content_type(self, chunks: List[StreamChunk]) -> str:
        """检测内容类型"""
        full_content = ''.join(chunk.content for chunk in chunks)
        
        # 检测代码
        if '```' in full_content or 'def ' in full_content or 'function ' in full_content:
            return "code"
        
        # 检测数学公式
        if '$' in full_content or '\\(' in full_content:
            return "math"
        
        # 检测表格
        if '|' in full_content and full_content.count('|') > 4:
            return "table"
        
        # 检测列表
        if full_content.count('\n-') > 2 or full_content.count('\n*') > 2:
            return "list"
        
        return "text"
    
    def _detect_language(self, chunks: List[StreamChunk]) -> str:
        """检测语言"""
        full_content = ''.join(chunk.content for chunk in chunks)
        
        # 简单的语言检测
        chinese_chars = sum(1 for char in full_content if '\u4e00' <= char <= '\u9fff')
        english_chars = sum(1 for char in full_content if char.isalpha() and ord(char) < 128)
        
        if chinese_chars > english_chars:
            return "chinese"
        elif english_chars > 0:
            return "english"
        else:
            return "unknown"
    
    def _calculate_quality_score(self, chunks: List[StreamChunk]) -> float:
        """计算质量分数"""
        if not chunks:
            return 0.0
        
        score = 1.0
        
        # 基于内容长度的评分
        total_length = sum(len(chunk.content) for chunk in chunks)
        if total_length < 10:
            score *= 0.5
        elif total_length > 1000:
            score *= 0.9
        
        # 基于数据块数量的评分
        if len(chunks) < 3:
            score *= 0.8
        elif len(chunks) > 100:
            score *= 0.9
        
        # 基于内容连贯性的评分
        coherence_score = self._calculate_coherence(chunks)
        score *= coherence_score
        
        return min(1.0, max(0.0, score))
    
    def _calculate_coherence(self, chunks: List[StreamChunk]) -> float:
        """计算内容连贯性"""
        if len(chunks) < 2:
            return 1.0
        
        # 检查数据块之间的连贯性
        coherence_score = 1.0
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1]
            curr_chunk = chunks[i]
            
            # 检查是否有突然的内容跳跃
            if len(prev_chunk.content) > 0 and len(curr_chunk.content) > 0:
                # 简单的连贯性检查
                if not curr_chunk.content[0].islower() and prev_chunk.content[-1] not in '.!?':
                    coherence_score *= 0.95
        
        return coherence_score
    
    def _detect_patterns(self, chunks: List[StreamChunk]) -> List[str]:
        """检测内容模式"""
        patterns = []
        full_content = ''.join(chunk.content for chunk in chunks)
        
        # 检测常见模式
        if '1.' in full_content and '2.' in full_content:
            patterns.append("numbered_list")
        
        if '- ' in full_content:
            patterns.append("bullet_list")
        
        if '```' in full_content:
            patterns.append("code_block")
        
        if '**' in full_content or '*' in full_content:
            patterns.append("markdown_formatting")
        
        return patterns
    
    def _analyze_performance(self, chunks: List[StreamChunk]) -> Dict[str, Any]:
        """分析性能指标"""
        if not chunks:
            return {}
        
        timestamps = [chunk.timestamp for chunk in chunks]
        if len(timestamps) < 2:
            return {"duration": 0, "rate": 0}
        
        duration = (timestamps[-1] - timestamps[0]).total_seconds()
        rate = len(chunks) / duration if duration > 0 else 0
        
        return {
            "duration": duration,
            "chunk_rate": rate,
            "avg_chunk_size": sum(len(chunk.content) for chunk in chunks) / len(chunks)
        }


# 全局实例
stream_optimizer = StreamOptimizer()
stream_analyzer = StreamAnalyzer()