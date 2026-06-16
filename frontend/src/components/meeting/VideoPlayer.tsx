import React, { useState, useRef, useEffect, useCallback } from 'react'
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Maximize, 
  Minimize, 
  SkipBack, 
  SkipForward,
  Settings,
  Download,
  Share2,
  MessageSquare,
  Bookmark,
  RotateCcw,
  RotateCw
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface VideoPlayerProps {
  src: string
  poster?: string
  title?: string
  duration?: number
  subtitles?: Array<{
    language: string
    label: string
    src: string
  }>
  chapters?: Array<{
    id: string
    title: string
    startTime: number
    endTime: number
  }>
  bookmarks?: Array<{
    id: string
    title: string
    time: number
    description?: string
  }>
  qualities?: Array<{
    label: string
    src: string
    resolution: string
  }>
  onProgress?: (progress: { currentTime: number; duration: number; percentage: number }) => void
  onPlay?: () => void
  onPause?: () => void
  onEnded?: () => void
  onTimeUpdate?: (currentTime: number) => void
  onQualityChange?: (quality: string) => void
  onBookmarkAdd?: (time: number, title: string) => void
  onBookmarkRemove?: (bookmarkId: string) => void
  allowDownload?: boolean
  allowShare?: boolean
  allowComments?: boolean
  autoQuality?: boolean
  resumePosition?: number
  className?: string
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  src,
  poster,
  title,
  duration,
  subtitles = [],
  chapters = [],
  bookmarks = [],
  qualities = [],
  onProgress,
  onPlay,
  onPause,
  onEnded,
  onTimeUpdate,
  onQualityChange,
  onBookmarkAdd,
  onBookmarkRemove,
  allowDownload = false,
  allowShare = false,
  allowComments = false,
  autoQuality = true,
  resumePosition = 0,
  className
}) => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const progressRef = useRef<HTMLDivElement>(null)
  
  // 播放状态
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [videoDuration, setVideoDuration] = useState(duration || 0)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [playbackRate, setPlaybackRate] = useState(1)
  
  // UI状态
  const [showControls, setShowControls] = useState(true)
  const [showSettings, setShowSettings] = useState(false)
  const [showChapters, setShowChapters] = useState(false)
  const [showSubtitles, setShowSubtitles] = useState(false)
  const [showBookmarks, setShowBookmarks] = useState(false)
  const [showQualityMenu, setShowQualityMenu] = useState(false)
  const [selectedSubtitle, setSelectedSubtitle] = useState<string>('')
  const [selectedQuality, setSelectedQuality] = useState<string>('')
  const [isBuffering, setIsBuffering] = useState(false)
  const [networkSpeed, setNetworkSpeed] = useState<number>(0)
  const [watchedSegments, setWatchedSegments] = useState<Array<{start: number, end: number}>>([])
  
  // 高级功能状态
  const [isAddingBookmark, setIsAddingBookmark] = useState(false)
  const [bookmarkTitle, setBookmarkTitle] = useState('')
  const [playbackStats, setPlaybackStats] = useState({
    totalWatchTime: 0,
    bufferEvents: 0,
    qualityChanges: 0
  })
  
  // 进度拖拽
  const [isDragging, setIsDragging] = useState(false)
  const [dragTime, setDragTime] = useState(0)
  
  // 控制栏自动隐藏
  const controlsTimeoutRef = useRef<NodeJS.Timeout>()
  
  // 键盘快捷键
  const handleKeyPress = useCallback((e: KeyboardEvent) => {
    if (!videoRef.current) return
    
    switch (e.code) {
      case 'Space':
        e.preventDefault()
        togglePlay()
        break
      case 'ArrowLeft':
        e.preventDefault()
        seek(currentTime - 10)
        break
      case 'ArrowRight':
        e.preventDefault()
        seek(currentTime + 10)
        break
      case 'ArrowUp':
        e.preventDefault()
        setVolume(Math.min(1, volume + 0.1))
        break
      case 'ArrowDown':
        e.preventDefault()
        setVolume(Math.max(0, volume - 0.1))
        break
      case 'KeyM':
        e.preventDefault()
        toggleMute()
        break
      case 'KeyF':
        e.preventDefault()
        toggleFullscreen()
        break
    }
  }, [currentTime, volume])
  
  useEffect(() => {
    document.addEventListener('keydown', handleKeyPress)
    return () => document.removeEventListener('keydown', handleKeyPress)
  }, [handleKeyPress])
  
  // 视频事件处理
  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setVideoDuration(videoRef.current.duration)
    }
  }
  
  const handleTimeUpdate = () => {
    if (videoRef.current && !isDragging) {
      const time = videoRef.current.currentTime
      setCurrentTime(time)
      onTimeUpdate?.(time)
      
      if (onProgress) {
        onProgress({
          currentTime: time,
          duration: videoDuration,
          percentage: (time / videoDuration) * 100
        })
      }
    }
  }
  
  const handlePlay = () => {
    setIsPlaying(true)
    onPlay?.()
  }
  
  const handlePause = () => {
    setIsPlaying(false)
    onPause?.()
  }
  
  const handleEnded = () => {
    setIsPlaying(false)
    onEnded?.()
  }
  
  const handleWaiting = () => {
    setIsBuffering(true)
    setPlaybackStats(prev => ({
      ...prev,
      bufferEvents: prev.bufferEvents + 1
    }))
  }
  
  const handleCanPlay = () => {
    setIsBuffering(false)
  }
  
  // 画中画功能
  const [isPictureInPicture, setIsPictureInPicture] = useState(false)
  
  const togglePictureInPicture = async () => {
    if (!videoRef.current) return
    
    try {
      if (isPictureInPicture) {
        await document.exitPictureInPicture()
      } else {
        await videoRef.current.requestPictureInPicture()
      }
    } catch (error) {
      console.error('画中画切换失败:', error)
    }
  }
  
  useEffect(() => {
    const handlePipEnter = () => setIsPictureInPicture(true)
    const handlePipLeave = () => setIsPictureInPicture(false)
    
    if (videoRef.current) {
      videoRef.current.addEventListener('enterpictureinpicture', handlePipEnter)
      videoRef.current.addEventListener('leavepictureinpicture', handlePipLeave)
      
      return () => {
        if (videoRef.current) {
          videoRef.current.removeEventListener('enterpictureinpicture', handlePipEnter)
          videoRef.current.removeEventListener('leavepictureinpicture', handlePipLeave)
        }
      }
    }
  }, [])
  
  // 截图功能
  const takeScreenshot = () => {
    if (!videoRef.current) return
    
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    
    canvas.width = videoRef.current.videoWidth
    canvas.height = videoRef.current.videoHeight
    
    ctx?.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height)
    
    canvas.toBlob(blob => {
      if (blob) {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `screenshot-${Date.now()}.png`
        a.click()
        URL.revokeObjectURL(url)
      }
    })
  }
  
  // 播放控制
  const togglePlay = () => {
    if (!videoRef.current) return
    
    if (isPlaying) {
      videoRef.current.pause()
    } else {
      videoRef.current.play()
    }
  }
  
  const seek = (time: number) => {
    if (!videoRef.current) return
    
    const clampedTime = Math.max(0, Math.min(videoDuration, time))
    videoRef.current.currentTime = clampedTime
    setCurrentTime(clampedTime)
  }
  
  const toggleMute = () => {
    if (!videoRef.current) return
    
    if (isMuted) {
      videoRef.current.volume = volume
      setIsMuted(false)
    } else {
      videoRef.current.volume = 0
      setIsMuted(true)
    }
  }
  
  const changeVolume = (newVolume: number) => {
    if (!videoRef.current) return
    
    const clampedVolume = Math.max(0, Math.min(1, newVolume))
    videoRef.current.volume = clampedVolume
    setVolume(clampedVolume)
    setIsMuted(clampedVolume === 0)
  }
  
  const changePlaybackRate = (rate: number) => {
    if (!videoRef.current) return
    
    videoRef.current.playbackRate = rate
    setPlaybackRate(rate)
  }
  
  // 质量切换
  const changeQuality = (qualityLabel: string) => {
    if (!videoRef.current) return
    
    const quality = qualities.find(q => q.label === qualityLabel)
    if (!quality) return
    
    const currentTime = videoRef.current.currentTime
    const wasPlaying = !videoRef.current.paused
    
    videoRef.current.src = quality.src
    videoRef.current.currentTime = currentTime
    
    if (wasPlaying) {
      videoRef.current.play()
    }
    
    setSelectedQuality(qualityLabel)
    onQualityChange?.(qualityLabel)
    
    setPlaybackStats(prev => ({
      ...prev,
      qualityChanges: prev.qualityChanges + 1
    }))
  }
  
  // 自动质量调整
  const adjustQualityBasedOnNetwork = useCallback(() => {
    if (!autoQuality || qualities.length === 0) return
    
    // 基于网络速度自动选择质量
    let recommendedQuality = qualities[0] // 默认最低质量
    
    if (networkSpeed > 5000) { // 5Mbps+
      recommendedQuality = qualities.find(q => q.resolution === '1080p') || qualities[qualities.length - 1]
    } else if (networkSpeed > 2000) { // 2Mbps+
      recommendedQuality = qualities.find(q => q.resolution === '720p') || qualities[Math.floor(qualities.length / 2)]
    } else if (networkSpeed > 1000) { // 1Mbps+
      recommendedQuality = qualities.find(q => q.resolution === '480p') || qualities[1]
    }
    
    if (recommendedQuality && recommendedQuality.label !== selectedQuality) {
      changeQuality(recommendedQuality.label)
    }
  }, [networkSpeed, autoQuality, qualities, selectedQuality])
  
  // 书签管理
  const addBookmark = () => {
    if (!bookmarkTitle.trim()) return
    
    onBookmarkAdd?.(currentTime, bookmarkTitle)
    setBookmarkTitle('')
    setIsAddingBookmark(false)
  }
  
  const removeBookmark = (bookmarkId: string) => {
    onBookmarkRemove?.(bookmarkId)
  }
  
  const jumpToBookmark = (time: number) => {
    seek(time)
    setShowBookmarks(false)
  }
  
  // 观看进度跟踪
  const updateWatchedSegments = useCallback(() => {
    const currentSegment = watchedSegments.find(segment => 
      currentTime >= segment.start && currentTime <= segment.end
    )
    
    if (!currentSegment) {
      // 创建新的观看片段
      setWatchedSegments(prev => [...prev, { start: currentTime, end: currentTime + 1 }])
    } else {
      // 扩展现有片段
      setWatchedSegments(prev => prev.map(segment => 
        segment === currentSegment 
          ? { ...segment, end: Math.max(segment.end, currentTime + 1) }
          : segment
      ))
    }
  }, [currentTime, watchedSegments])
  
  // 网络速度监测
  const measureNetworkSpeed = useCallback(async () => {
    try {
      const startTime = Date.now()
      const response = await fetch('/api/speed-test', { method: 'HEAD' })
      const endTime = Date.now()
      
      if (response.ok) {
        const duration = (endTime - startTime) / 1000
        const speed = (1024 * 8) / duration // 假设1KB测试文件
        setNetworkSpeed(speed)
      }
    } catch (error) {
      console.error('网络速度测试失败:', error)
    }
  }, [])
  
  // 播放统计更新
  useEffect(() => {
    if (isPlaying) {
      const interval = setInterval(() => {
        setPlaybackStats(prev => ({
          ...prev,
          totalWatchTime: prev.totalWatchTime + 1
        }))
        updateWatchedSegments()
      }, 1000)
      
      return () => clearInterval(interval)
    }
  }, [isPlaying, updateWatchedSegments])
  
  // 恢复播放位置
  useEffect(() => {
    if (resumePosition > 0 && videoRef.current) {
      videoRef.current.currentTime = resumePosition
    }
  }, [resumePosition])
  
  // 网络质量监测
  useEffect(() => {
    measureNetworkSpeed()
    const interval = setInterval(measureNetworkSpeed, 30000) // 每30秒检测一次
    
    return () => clearInterval(interval)
  }, [measureNetworkSpeed])
  
  // 自动质量调整
  useEffect(() => {
    adjustQualityBasedOnNetwork()
  }, [adjustQualityBasedOnNetwork])
  
  // 全屏控制
  const toggleFullscreen = () => {
    if (!containerRef.current) return
    
    if (!isFullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen()
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen()
      }
    }
  }
  
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])
  
  // 进度条拖拽
  const handleProgressMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true)
    updateProgressFromMouse(e)
  }
  
  const handleProgressMouseMove = useCallback((e: MouseEvent) => {
    if (isDragging) {
      updateProgressFromMouse(e as any)
    }
  }, [isDragging])
  
  const handleProgressMouseUp = useCallback(() => {
    if (isDragging) {
      setIsDragging(false)
      seek(dragTime)
    }
  }, [isDragging, dragTime])
  
  const updateProgressFromMouse = (e: React.MouseEvent | MouseEvent) => {
    if (!progressRef.current) return
    
    const rect = progressRef.current.getBoundingClientRect()
    const percentage = (e.clientX - rect.left) / rect.width
    const time = percentage * videoDuration
    setDragTime(time)
    
    if (!isDragging) {
      seek(time)
    }
  }
  
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleProgressMouseMove)
      document.addEventListener('mouseup', handleProgressMouseUp)
      
      return () => {
        document.removeEventListener('mousemove', handleProgressMouseMove)
        document.removeEventListener('mouseup', handleProgressMouseUp)
      }
    }
  }, [isDragging, handleProgressMouseMove, handleProgressMouseUp])
  
  // 控制栏自动隐藏
  const showControlsTemporarily = () => {
    setShowControls(true)
    
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current)
    }
    
    controlsTimeoutRef.current = setTimeout(() => {
      if (isPlaying) {
        setShowControls(false)
      }
    }, 3000)
  }
  
  const handleMouseMove = () => {
    showControlsTemporarily()
  }
  
  // 格式化时间
  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }
  
  // 获取当前章节
  const getCurrentChapter = () => {
    return chapters.find(chapter => 
      currentTime >= chapter.startTime && currentTime < chapter.endTime
    )
  }
  
  const currentChapter = getCurrentChapter()
  
  return (
    <div 
      ref={containerRef}
      className={cn(
        'relative bg-black rounded-lg overflow-hidden group',
        isFullscreen && 'fixed inset-0 z-50 rounded-none',
        className
      )}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setShowControls(false)}
    >
      {/* 视频元素 */}
      <video
        ref={videoRef}
        src={src}
        poster={poster}
        className="w-full h-full object-contain"
        onLoadedMetadata={handleLoadedMetadata}
        onTimeUpdate={handleTimeUpdate}
        onPlay={handlePlay}
        onPause={handlePause}
        onEnded={handleEnded}
        onWaiting={handleWaiting}
        onCanPlay={handleCanPlay}
        preload="metadata"
      >
        {subtitles.map(subtitle => (
          <track
            key={subtitle.language}
            kind="subtitles"
            src={subtitle.src}
            srcLang={subtitle.language}
            label={subtitle.label}
            default={subtitle.language === selectedSubtitle}
          />
        ))}
      </video>
      
      {/* 加载指示器 */}
      {isBuffering && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      
      {/* 播放按钮覆盖层 */}
      {!isPlaying && !isBuffering && (
        <div 
          className="absolute inset-0 flex items-center justify-center cursor-pointer"
          onClick={togglePlay}
        >
          <div className="w-16 h-16 bg-black bg-opacity-50 rounded-full flex items-center justify-center hover:bg-opacity-70 transition-all">
            <Play className="w-8 h-8 text-white ml-1" />
          </div>
        </div>
      )}
      
      {/* 控制栏 */}
      <div className={cn(
        'absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-4 transition-opacity duration-300',
        showControls || !isPlaying ? 'opacity-100' : 'opacity-0'
      )}>
        {/* 进度条 */}
        <div className="mb-4">
          <div 
            ref={progressRef}
            className="relative h-1 bg-white bg-opacity-30 rounded-full cursor-pointer hover:h-2 transition-all dark:bg-gray-800"
            onMouseDown={handleProgressMouseDown}
          >
            {/* 观看进度背景 */}
            {watchedSegments.map((segment, index) => (
              <div
                key={index}
                className="absolute top-0 h-full bg-gray-400 bg-opacity-30 rounded-full dark:bg-gray-500"
                style={{
                  left: `${(segment.start / videoDuration) * 100}%`,
                  width: `${((segment.end - segment.start) / videoDuration) * 100}%`
                }}
              />
            ))}
            
            {/* 缓冲进度 */}
            <div 
              className="absolute top-0 left-0 h-full bg-white bg-opacity-50 rounded-full dark:bg-gray-800"
              style={{ width: '0%' }} // 这里应该根据实际缓冲进度设置
            />
            
            {/* 播放进度 */}
            <div 
              className="absolute top-0 left-0 h-full bg-blue-500 rounded-full"
              style={{ width: `${((isDragging ? dragTime : currentTime) / videoDuration) * 100}%` }}
            />
            
            {/* 章节标记 */}
            {chapters.map(chapter => (
              <div
                key={chapter.id}
                className="absolute top-0 w-0.5 h-full bg-yellow-400"
                style={{ left: `${(chapter.startTime / videoDuration) * 100}%` }}
                title={chapter.title}
              />
            ))}
            
            {/* 书签标记 */}
            {bookmarks.map(bookmark => (
              <div
                key={bookmark.id}
                className="absolute top-0 w-1 h-full bg-green-400 cursor-pointer"
                style={{ left: `${(bookmark.time / videoDuration) * 100}%` }}
                title={bookmark.title}
                onClick={() => jumpToBookmark(bookmark.time)}
              />
            ))}
            
            {/* 拖拽手柄 */}
            <div 
              className="absolute top-1/2 w-3 h-3 bg-blue-500 rounded-full transform -translate-y-1/2 -translate-x-1/2 opacity-0 hover:opacity-100 transition-opacity"
              style={{ left: `${((isDragging ? dragTime : currentTime) / videoDuration) * 100}%` }}
            />
          </div>
          
          {/* 时间显示 */}
          <div className="flex justify-between items-center mt-2 text-sm text-white">
            <span>{formatTime(isDragging ? dragTime : currentTime)} / {formatTime(videoDuration)}</span>
            {currentChapter && (
              <span className="text-yellow-400">{currentChapter.title}</span>
            )}
          </div>
        </div>
        
        {/* 控制按钮 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {/* 播放/暂停 */}
            <button
              onClick={togglePlay}
              className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            </button>
            
            {/* 快退/快进 */}
            <button
              onClick={() => seek(currentTime - 10)}
              className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
            >
              <SkipBack className="w-4 h-4" />
            </button>
            
            <button
              onClick={() => seek(currentTime + 10)}
              className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
            >
              <SkipForward className="w-4 h-4" />
            </button>
            
            {/* 音量控制 */}
            <div className="flex items-center space-x-2">
              <button
                onClick={toggleMute}
                className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
              >
                {isMuted || volume === 0 ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </button>
              
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={isMuted ? 0 : volume}
                onChange={(e) => changeVolume(parseFloat(e.target.value))}
                className="w-20 h-1 bg-white bg-opacity-30 rounded-full appearance-none cursor-pointer dark:bg-gray-800"
              />
            </div>
            
            {/* 播放速度 */}
            <div className="relative">
              <select
                value={playbackRate}
                onChange={(e) => changePlaybackRate(parseFloat(e.target.value))}
                className="bg-transparent text-white text-sm border border-white border-opacity-30 rounded px-2 py-1"
              >
                <option value={0.5}>0.5x</option>
                <option value={0.75}>0.75x</option>
                <option value={1}>1x</option>
                <option value={1.25}>1.25x</option>
                <option value={1.5}>1.5x</option>
                <option value={2}>2x</option>
              </select>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* 章节 */}
            {chapters.length > 0 && (
              <button
                onClick={() => setShowChapters(!showChapters)}
                className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
                title="章节"
              >
                <Bookmark className="w-4 h-4" />
              </button>
            )}
            
            {/* 书签 */}
            <button
              onClick={() => setShowBookmarks(!showBookmarks)}
              className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
              title="书签"
            >
              <Bookmark className="w-4 h-4" />
            </button>
            
            {/* 质量选择 */}
            {qualities.length > 0 && (
              <div className="relative">
                <button
                  onClick={() => setShowQualityMenu(!showQualityMenu)}
                  className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors text-xs dark:bg-gray-800"
                  title="视频质量"
                >
                  {selectedQuality || 'Auto'}
                </button>
                
                {showQualityMenu && (
                  <div className="absolute bottom-full mb-2 right-0 bg-black bg-opacity-90 rounded-lg p-2 min-w-24">
                    {autoQuality && (
                      <button
                        onClick={() => {
                          setSelectedQuality('')
                          setShowQualityMenu(false)
                        }}
                        className={cn(
                          'block w-full text-left px-2 py-1 text-xs rounded transition-colors',
                          selectedQuality === ''
                            ? 'bg-blue-500 text-white'
                            : 'text-gray-300 hover:bg-white hover:bg-opacity-10 dark:bg-gray-800'
                        )}
                      >
                        Auto
                      </button>
                    )}
                    {qualities.map(quality => (
                      <button
                        key={quality.label}
                        onClick={() => {
                          changeQuality(quality.label)
                          setShowQualityMenu(false)
                        }}
                        className={cn(
                          'block w-full text-left px-2 py-1 text-xs rounded transition-colors',
                          selectedQuality === quality.label
                            ? 'bg-blue-500 text-white'
                            : 'text-gray-300 hover:bg-white hover:bg-opacity-10 dark:bg-gray-800'
                        )}
                      >
                        {quality.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* 画中画 */}
            {document.pictureInPictureEnabled && (
              <button
                onClick={togglePictureInPicture}
                className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
                title="画中画"
              >
                <div className="w-4 h-4 border border-current rounded flex items-center justify-center">
                  <div className="w-2 h-1.5 bg-current rounded-sm" />
                </div>
              </button>
            )}
            
            {/* 字幕 */}
            {subtitles.length > 0 && (
              <button
                onClick={() => setShowSubtitles(!showSubtitles)}
                className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
                title="字幕"
              >
                <MessageSquare className="w-4 h-4" />
              </button>
            )}
            
            {/* 设置 */}
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
            >
              <Settings className="w-4 h-4" />
            </button>
            
            {/* 下载 */}
            {allowDownload && (
              <button
                onClick={() => {/* 实现下载逻辑 */}}
                className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
                title="下载"
              >
                <Download className="w-4 h-4" />
              </button>
            )}
            
            {/* 分享 */}
            {allowShare && (
              <button
                onClick={() => {/* 实现分享逻辑 */}}
                className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
                title="分享"
              >
                <Share2 className="w-4 h-4" />
              </button>
            )}
            
            {/* 全屏 */}
            <button
              onClick={toggleFullscreen}
              className="p-2 text-white hover:bg-white hover:bg-opacity-20 rounded transition-colors dark:bg-gray-800"
            >
              {isFullscreen ? <Minimize className="w-4 h-4" /> : <Maximize className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
      
      {/* 章节列表 */}
      {showChapters && (
        <div className="absolute right-4 bottom-20 w-64 bg-black bg-opacity-90 rounded-lg p-4 max-h-64 overflow-y-auto">
          <h3 className="text-white font-medium mb-2">章节</h3>
          <div className="space-y-2">
            {chapters.map(chapter => (
              <button
                key={chapter.id}
                onClick={() => {
                  seek(chapter.startTime)
                  setShowChapters(false)
                }}
                className={cn(
                  'w-full text-left p-2 rounded text-sm transition-colors',
                  currentChapter?.id === chapter.id
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-300 hover:bg-white hover:bg-opacity-10 dark:bg-gray-800'
                )}
              >
                <div className="font-medium">{chapter.title}</div>
                <div className="text-xs opacity-70">
                  {formatTime(chapter.startTime)} - {formatTime(chapter.endTime)}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* 字幕选择 */}
      {showSubtitles && (
        <div className="absolute right-4 bottom-20 w-48 bg-black bg-opacity-90 rounded-lg p-4">
          <h3 className="text-white font-medium mb-2">字幕</h3>
          <div className="space-y-1">
            <button
              onClick={() => {
                setSelectedSubtitle('')
                setShowSubtitles(false)
              }}
              className={cn(
                'w-full text-left p-2 rounded text-sm transition-colors',
                selectedSubtitle === ''
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-300 hover:bg-white hover:bg-opacity-10 dark:bg-gray-800'
              )}
            >
              关闭字幕
            </button>
            {subtitles.map(subtitle => (
              <button
                key={subtitle.language}
                onClick={() => {
                  setSelectedSubtitle(subtitle.language)
                  setShowSubtitles(false)
                }}
                className={cn(
                  'w-full text-left p-2 rounded text-sm transition-colors',
                  selectedSubtitle === subtitle.language
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-300 hover:bg-white hover:bg-opacity-10 dark:bg-gray-800'
                )}
              >
                {subtitle.label}
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* 书签管理 */}
      {showBookmarks && (
        <div className="absolute right-4 bottom-20 w-64 bg-black bg-opacity-90 rounded-lg p-4 max-h-64 overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-white font-medium">书签</h3>
            <button
              onClick={() => setIsAddingBookmark(true)}
              className="text-blue-400 hover:text-blue-300 text-sm"
            >
              + 添加
            </button>
          </div>
          
          {isAddingBookmark && (
            <div className="mb-3 p-2 bg-gray-800 rounded">
              <input
                type="text"
                value={bookmarkTitle}
                onChange={(e) => setBookmarkTitle(e.target.value)}
                placeholder="书签标题"
                className="w-full bg-transparent text-white text-sm border-b border-gray-600 pb-1 mb-2 focus:outline-none focus:border-blue-400"
                autoFocus
              />
              <div className="flex space-x-2">
                <button
                  onClick={addBookmark}
                  className="px-2 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600"
                >
                  保存
                </button>
                <button
                  onClick={() => {
                    setIsAddingBookmark(false)
                    setBookmarkTitle('')
                  }}
                  className="px-2 py-1 bg-gray-600 text-white text-xs rounded hover:bg-gray-700"
                >
                  取消
                </button>
              </div>
            </div>
          )}
          
          <div className="space-y-2">
            {bookmarks.map(bookmark => (
              <div
                key={bookmark.id}
                className="flex items-center justify-between p-2 rounded hover:bg-white hover:bg-opacity-10 dark:bg-gray-800"
              >
                <button
                  onClick={() => jumpToBookmark(bookmark.time)}
                  className="flex-1 text-left"
                >
                  <div className="text-white text-sm font-medium">{bookmark.title}</div>
                  <div className="text-gray-400 text-xs dark:text-gray-500">{formatTime(bookmark.time)}</div>
                  {bookmark.description && (
                    <div className="text-gray-400 text-xs mt-1 dark:text-gray-500">{bookmark.description}</div>
                  )}
                </button>
                <button
                  onClick={() => removeBookmark(bookmark.id)}
                  className="text-red-400 hover:text-red-300 text-xs ml-2"
                >
                  删除
                </button>
              </div>
            ))}
            
            {bookmarks.length === 0 && !isAddingBookmark && (
              <div className="text-gray-400 text-sm text-center py-4 dark:text-gray-500">
                暂无书签
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* 播放统计信息 */}
      {showSettings && (
        <div className="absolute right-4 bottom-20 w-64 bg-black bg-opacity-90 rounded-lg p-4">
          <h3 className="text-white font-medium mb-3">播放信息</h3>
          
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-gray-300">
              <span>观看时长:</span>
              <span>{Math.floor(playbackStats.totalWatchTime / 60)}分{playbackStats.totalWatchTime % 60}秒</span>
            </div>
            
            <div className="flex justify-between text-gray-300">
              <span>缓冲次数:</span>
              <span>{playbackStats.bufferEvents}</span>
            </div>
            
            <div className="flex justify-between text-gray-300">
              <span>质量切换:</span>
              <span>{playbackStats.qualityChanges}</span>
            </div>
            
            <div className="flex justify-between text-gray-300">
              <span>网络速度:</span>
              <span>{(networkSpeed / 1000).toFixed(1)} Mbps</span>
            </div>
            
            <div className="flex justify-between text-gray-300">
              <span>当前质量:</span>
              <span>{selectedQuality || 'Auto'}</span>
            </div>
            
            <div className="flex justify-between text-gray-300">
              <span>播放速度:</span>
              <span>{playbackRate}x</span>
            </div>
          </div>
          
          <div className="mt-4 pt-3 border-t border-gray-700">
            <button
              onClick={takeScreenshot}
              className="w-full p-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 transition-colors"
            >
              截图
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default VideoPlayer