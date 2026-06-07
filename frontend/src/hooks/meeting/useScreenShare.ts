// 屏幕共享自定义Hook
import { useState, useCallback, useRef, useEffect } from 'react'

export interface ShareOptions {
  type: 'screen' | 'window' | 'tab'
  audio?: boolean
  cursor?: boolean
  quality?: 'low' | 'medium' | 'high'
}

export interface ScreenShareState {
  isSharing: boolean
  shareStream: MediaStream | null
  sharerName: string | null
  hasPermission: boolean
  error: string | null
}

export interface ScreenSharePermissions {
  canShare: boolean
  canControl: boolean
  canAnnotate: boolean
  canStop: boolean
}

export const useScreenShare = (meetingId?: string) => {
  // 状态管理
  const [state, setState] = useState<ScreenShareState>({
    isSharing: false,
    shareStream: null,
    sharerName: null,
    hasPermission: false,
    error: null
  })

  const [permissions, setPermissions] = useState<ScreenSharePermissions>({
    canShare: true,
    canControl: false,
    canAnnotate: true,
    canStop: false
  })

  const streamRef = useRef<MediaStream | null>(null)

  // 检查浏览器支持
  const checkBrowserSupport = useCallback(() => {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia)
  }, [])

  // 请求屏幕共享权限
  const requestPermission = useCallback(async (): Promise<boolean> => {
    try {
      if (!checkBrowserSupport()) {
        setState(prev => ({ ...prev, error: '浏览器不支持屏幕共享功能' }))
        return false
      }

      // 检查权限状态
      const permission = await navigator.permissions?.query?.({ name: 'display-capture' as any })
      const hasPermission = !permission || permission.state !== 'denied'
      
      setState(prev => ({ ...prev, hasPermission, error: null }))
      return hasPermission
    } catch (error) {
      console.error('检查屏幕共享权限失败:', error)
      setState(prev => ({ ...prev, hasPermission: false, error: '无法检查屏幕共享权限' }))
      return false
    }
  }, [checkBrowserSupport])

  // 开始屏幕共享
  const startScreenShare = useCallback(async (options: ShareOptions): Promise<MediaStream | null> => {
    try {
      setState(prev => ({ ...prev, error: null }))

      // 检查权限
      const hasPermission = await requestPermission()
      if (!hasPermission) {
        throw new Error('没有屏幕共享权限')
      }

      // 配置媒体约束
      const constraints: any = {
        video: {
          cursor: options.cursor ? 'always' : 'never',
          displaySurface: options.type === 'screen' ? 'monitor' : 
                         options.type === 'window' ? 'window' : 'browser'
        },
        audio: options.audio || false
      }

      // 根据质量设置视频约束
      if (constraints.video && typeof constraints.video === 'object') {
        switch (options.quality) {
          case 'low':
            constraints.video.width = { max: 1280 }
            constraints.video.height = { max: 720 }
            constraints.video.frameRate = { max: 15 }
            break
          case 'medium':
            constraints.video.width = { max: 1920 }
            constraints.video.height = { max: 1080 }
            constraints.video.frameRate = { max: 30 }
            break
          case 'high':
            constraints.video.width = { max: 3840 }
            constraints.video.height = { max: 2160 }
            constraints.video.frameRate = { max: 60 }
            break
        }
      }

      // 获取屏幕共享流
      const stream = await navigator.mediaDevices.getDisplayMedia(constraints)
      streamRef.current = stream

      // 监听流结束事件
      stream.getVideoTracks()[0]?.addEventListener('ended', () => {
        stopScreenShare()
      })

      setState(prev => ({
        ...prev,
        isSharing: true,
        shareStream: stream,
        sharerName: '我', // 当前用户
        error: null
      }))

      // 通知其他参与者开始屏幕共享
      if (meetingId) {
        await notifyScreenShareStart(meetingId, options)
      }

      return stream
    } catch (error) {
      console.error('开始屏幕共享失败:', error)
      const errorMessage = error instanceof Error ? error.message : '开始屏幕共享失败'
      setState(prev => ({ ...prev, error: errorMessage }))
      return null
    }
  }, [meetingId, requestPermission])

  // 停止屏幕共享
  const stopScreenShare = useCallback(async () => {
    try {
      // 停止所有轨道
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => {
          track.stop()
        })
        streamRef.current = null
      }

      setState(prev => ({
        ...prev,
        isSharing: false,
        shareStream: null,
        sharerName: null,
        error: null
      }))

      // 通知其他参与者停止屏幕共享
      if (meetingId) {
        await notifyScreenShareStop(meetingId)
      }
    } catch (error) {
      console.error('停止屏幕共享失败:', error)
      setState(prev => ({ ...prev, error: '停止屏幕共享失败' }))
    }
  }, [meetingId])

  // 请求控制权限
  const requestControl = useCallback(async (): Promise<boolean> => {
    try {
      if (!meetingId) return false

      // 发送控制权限请求
      const response = await fetch(`/api/meetings/${meetingId}/screen-share/request-control`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (response.ok) {
        setPermissions(prev => ({ ...prev, canControl: true }))
        return true
      }

      return false
    } catch (error) {
      console.error('请求控制权限失败:', error)
      return false
    }
  }, [meetingId])

  // 释放控制权限
  const releaseControl = useCallback(async () => {
    try {
      if (!meetingId) return

      await fetch(`/api/meetings/${meetingId}/screen-share/release-control`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      setPermissions(prev => ({ ...prev, canControl: false }))
    } catch (error) {
      console.error('释放控制权限失败:', error)
    }
  }, [meetingId])

  // 通知屏幕共享开始
  const notifyScreenShareStart = useCallback(async (meetingId: string, options: ShareOptions) => {
    try {
      await fetch(`/api/meetings/${meetingId}/screen-share/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(options)
      })
    } catch (error) {
      console.error('通知屏幕共享开始失败:', error)
    }
  }, [])

  // 通知屏幕共享停止
  const notifyScreenShareStop = useCallback(async (meetingId: string) => {
    try {
      await fetch(`/api/meetings/${meetingId}/screen-share/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
    } catch (error) {
      console.error('通知屏幕共享停止失败:', error)
    }
  }, [])

  // 清理资源
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => {
          track.stop()
        })
      }
    }
  }, [])

  // 初始化权限检查
  useEffect(() => {
    requestPermission()
  }, [requestPermission])

  return {
    // 状态
    ...state,
    permissions,
    
    // 方法
    startScreenShare,
    stopScreenShare,
    requestControl,
    releaseControl,
    requestPermission,
    checkBrowserSupport
  }
}

export default useScreenShare