import { useState, useEffect, useCallback, useRef } from 'react'
import { RecordingService, RecordingConfig, RecordingStatus, StartRecordingRequest } from '@/services/recordingService'
import { toast } from 'sonner'

export interface UseRecordingOptions {
  meetingId: number
  autoCheckPermissions?: boolean
  onRecordingStart?: (recording: RecordingStatus) => void
  onRecordingStop?: (recording: RecordingStatus) => void
  onRecordingError?: (error: Error) => void
  onStatusUpdate?: (recording: RecordingStatus) => void
}

export interface RecordingPermissions {
  canRecord: boolean
  canStart: boolean
  canStop: boolean
  canPause: boolean
  reason?: string
}

export interface StorageQuota {
  used: number
  total: number
  available: number
  unit: string
}

export const useRecording = (options: UseRecordingOptions) => {
  const { 
    meetingId, 
    autoCheckPermissions = true,
    onRecordingStart,
    onRecordingStop,
    onRecordingError,
    onStatusUpdate
  } = options

  // 状态管理
  const [recordings, setRecordings] = useState<RecordingStatus[]>([])
  const [activeRecording, setActiveRecording] = useState<RecordingStatus | null>(null)
  const [permissions, setPermissions] = useState<RecordingPermissions>({
    canRecord: false,
    canStart: false,
    canStop: false,
    canPause: false
  })
  const [storageQuota, setStorageQuota] = useState<StorageQuota | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 定时器引用
  const statusCheckInterval = useRef<NodeJS.Timeout>()
  const durationTimer = useRef<NodeJS.Timeout>()

  /**
   * 检查录制权限
   */
  const checkPermissions = useCallback(async () => {
    try {
      const perms = await RecordingService.checkRecordingPermission(meetingId)
      setPermissions(perms)
      
      if (!perms.canRecord && perms.reason) {
        setError(perms.reason)
      }
    } catch (err) {
      console.error('检查录制权限失败:', err)
      setError('无法检查录制权限')
    }
  }, [meetingId])

  /**
   * 获取存储配额
   */
  const getStorageQuota = useCallback(async () => {
    try {
      const quota = await RecordingService.getStorageQuota()
      setStorageQuota(quota)
    } catch (err) {
      console.error('获取存储配额失败:', err)
    }
  }, [])

  /**
   * 获取会议录制列表
   */
  const loadRecordings = useCallback(async () => {
    try {
      setIsLoading(true)
      const recordingList = await RecordingService.getMeetingRecordings(meetingId)
      setRecordings(recordingList)
      
      // 查找活跃的录制
      const active = recordingList.find(r => r.recordingStatus === 'RECORDING')
      setActiveRecording(active || null)
    } catch (err) {
      console.error('获取录制列表失败:', err)
      setError('无法获取录制列表')
    } finally {
      setIsLoading(false)
    }
  }, [meetingId])

  /**
   * 开始录制
   */
  const startRecording = useCallback(async (config: RecordingConfig, recordingName?: string) => {
    if (!permissions.canStart) {
      const message = '没有开始录制的权限'
      setError(message)
      onRecordingError?.(new Error(message))
      return null
    }

    try {
      setIsLoading(true)
      setError(null)

      const request: StartRecordingRequest = {
        meetingId,
        recordingName,
        recordingType: 'FULL_MEETING',
        fileFormat: config.format.toUpperCase() as 'MP4' | 'WEBM',
        config
      }

      const recording = await RecordingService.startRecording(request)
      
      setActiveRecording(recording)
      setRecordings(prev => [...prev, recording])
      
      // 开始状态检查定时器
      startStatusCheck(recording.id)
      
      toast.success('录制已开始')
      onRecordingStart?.(recording)
      
      return recording
    } catch (err: any) {
      const message = err.response?.data?.message || '开始录制失败'
      setError(message)
      onRecordingError?.(new Error(message))
      toast.error(message)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [meetingId, permissions.canStart, onRecordingStart, onRecordingError])

  /**
   * 停止录制
   */
  const stopRecording = useCallback(async () => {
    if (!activeRecording || !permissions.canStop) {
      const message = '没有停止录制的权限'
      setError(message)
      onRecordingError?.(new Error(message))
      return null
    }

    try {
      setIsLoading(true)
      setError(null)

      const recording = await RecordingService.stopRecording(activeRecording.id)
      
      setActiveRecording(null)
      setRecordings(prev => prev.map(r => r.id === recording.id ? recording : r))
      
      // 停止状态检查定时器
      stopStatusCheck()
      
      toast.success('录制已停止，正在处理中...')
      onRecordingStop?.(recording)
      
      return recording
    } catch (err: any) {
      const message = err.response?.data?.message || '停止录制失败'
      setError(message)
      onRecordingError?.(new Error(message))
      toast.error(message)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [activeRecording, permissions.canStop, onRecordingStop, onRecordingError])

  /**
   * 暂停录制
   */
  const pauseRecording = useCallback(async () => {
    if (!activeRecording || !permissions.canPause) {
      const message = '没有暂停录制的权限'
      setError(message)
      onRecordingError?.(new Error(message))
      return null
    }

    try {
      setIsLoading(true)
      setError(null)

      const recording = await RecordingService.pauseRecording(activeRecording.id)
      
      setActiveRecording(recording)
      setRecordings(prev => prev.map(r => r.id === recording.id ? recording : r))
      
      toast.success('录制已暂停')
      onStatusUpdate?.(recording)
      
      return recording
    } catch (err: any) {
      const message = err.response?.data?.message || '暂停录制失败'
      setError(message)
      onRecordingError?.(new Error(message))
      toast.error(message)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [activeRecording, permissions.canPause, onRecordingError, onStatusUpdate])

  /**
   * 恢复录制
   */
  const resumeRecording = useCallback(async () => {
    if (!activeRecording || !permissions.canPause) {
      const message = '没有恢复录制的权限'
      setError(message)
      onRecordingError?.(new Error(message))
      return null
    }

    try {
      setIsLoading(true)
      setError(null)

      const recording = await RecordingService.resumeRecording(activeRecording.id)
      
      setActiveRecording(recording)
      setRecordings(prev => prev.map(r => r.id === recording.id ? recording : r))
      
      toast.success('录制已恢复')
      onStatusUpdate?.(recording)
      
      return recording
    } catch (err: any) {
      const message = err.response?.data?.message || '恢复录制失败'
      setError(message)
      onRecordingError?.(new Error(message))
      toast.error(message)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [activeRecording, permissions.canPause, onRecordingError, onStatusUpdate])

  /**
   * 开始状态检查
   */
  const startStatusCheck = useCallback((recordingId: number) => {
    stopStatusCheck() // 先停止之前的定时器
    
    statusCheckInterval.current = setInterval(async () => {
      try {
        const recording = await RecordingService.getRecordingDetails(recordingId)
        
        setActiveRecording(prev => {
          if (prev && prev.id === recordingId) {
            return recording
          }
          return prev
        })
        
        setRecordings(prev => prev.map(r => r.id === recordingId ? recording : r))
        
        onStatusUpdate?.(recording)
        
        // 如果录制已完成或失败，停止检查
        if (recording.recordingStatus === 'COMPLETED' || recording.recordingStatus === 'FAILED') {
          stopStatusCheck()
          if (recording.recordingStatus === 'COMPLETED') {
            toast.success('录制处理完成')
          } else {
            toast.error('录制处理失败')
          }
        }
      } catch (err) {
        console.error('检查录制状态失败:', err)
      }
    }, 2000) // 每2秒检查一次
  }, [onStatusUpdate])

  /**
   * 停止状态检查
   */
  const stopStatusCheck = useCallback(() => {
    if (statusCheckInterval.current) {
      clearInterval(statusCheckInterval.current)
      statusCheckInterval.current = undefined
    }
  }, [])

  /**
   * 删除录制
   */
  const deleteRecording = useCallback(async (recordingId: number) => {
    try {
      await RecordingService.deleteRecording(recordingId)
      
      setRecordings(prev => prev.filter(r => r.id !== recordingId))
      
      if (activeRecording?.id === recordingId) {
        setActiveRecording(null)
        stopStatusCheck()
      }
      
      toast.success('录制已删除')
    } catch (err: any) {
      const message = err.response?.data?.message || '删除录制失败'
      setError(message)
      toast.error(message)
    }
  }, [activeRecording?.id])

  /**
   * 获取录制播放信息
   */
  const getPlaybackInfo = useCallback(async (recordingId: number) => {
    try {
      return await RecordingService.getPlaybackInfo(recordingId)
    } catch (err: any) {
      const message = err.response?.data?.message || '获取播放信息失败'
      setError(message)
      toast.error(message)
      return null
    }
  }, [])

  // 初始化
  useEffect(() => {
    if (autoCheckPermissions) {
      checkPermissions()
    }
    loadRecordings()
    getStorageQuota()
  }, [autoCheckPermissions, checkPermissions, loadRecordings, getStorageQuota])

  // 清理定时器
  useEffect(() => {
    return () => {
      stopStatusCheck()
      if (durationTimer.current) {
        clearInterval(durationTimer.current)
      }
    }
  }, [stopStatusCheck])

  // 计算录制状态
  const recordingState = {
    isRecording: activeRecording?.recordingStatus === 'RECORDING',
    isPaused: activeRecording?.recordingStatus === 'RECORDING' && false, // TODO: 添加暂停状态支持
    isProcessing: activeRecording?.recordingStatus === 'PROCESSING',
    isCompleted: recordings.some(r => r.recordingStatus === 'COMPLETED'),
    hasError: recordings.some(r => r.recordingStatus === 'FAILED')
  }

  return {
    // 状态
    recordings,
    activeRecording,
    permissions,
    storageQuota,
    isLoading,
    error,
    recordingState,
    
    // 操作方法
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    deleteRecording,
    getPlaybackInfo,
    
    // 工具方法
    checkPermissions,
    loadRecordings,
    getStorageQuota,
    
    // 清理方法
    clearError: () => setError(null)
  }
}

export default useRecording