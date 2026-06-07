// 文件共享自定义Hook
import { useState, useCallback, useEffect } from 'react'
import { fileService, type SharedFile, type FileUploadOptions } from '@/services/fileService'

interface UseFileShareOptions {
  meetingId?: number
  maxFileSize?: number // MB
  allowedTypes?: string[]
  autoRefresh?: boolean
  refreshInterval?: number // ms
}

interface UploadProgress {
  [fileId: string]: number
}

export const useFileShare = (options: UseFileShareOptions = {}) => {
  const {
    meetingId,
    maxFileSize = 100,
    allowedTypes = ['*'],
    autoRefresh = false,
    refreshInterval = 30000
  } = options

  // 状态管理
  const [files, setFiles] = useState<SharedFile[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({})
  const [error, setError] = useState<string | null>(null)

  // 获取文件列表
  const fetchFiles = useCallback(async () => {
    if (!meetingId) return

    setLoading(true)
    setError(null)

    try {
      const fileList = await fileService.getMeetingFiles(meetingId)
      setFiles(fileList)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取文件列表失败'
      setError(errorMessage)
      console.error('获取文件列表失败:', err)
    } finally {
      setLoading(false)
    }
  }, [meetingId])

  // 上传文件
  const uploadFiles = useCallback(async (fileList: FileList) => {
    if (!meetingId) {
      setError('会议ID不能为空')
      return
    }

    setUploading(true)
    setError(null)

    const validFiles: File[] = []
    const errors: string[] = []

    // 验证文件
    Array.from(fileList).forEach(file => {
      const validation = fileService.validateFile(file, {
        maxSize: maxFileSize,
        allowedTypes
      })

      if (validation.valid) {
        validFiles.push(file)
      } else {
        errors.push(`${file.name}: ${validation.error}`)
      }
    })

    if (errors.length > 0) {
      setError(`文件验证失败:\n${errors.join('\n')}`)
      setUploading(false)
      return
    }

    try {
      const uploadOptions: FileUploadOptions = {
        meetingId,
        isPublic: false
      }

      // 创建临时文件记录用于显示进度
      const tempFiles: SharedFile[] = validFiles.map(file => ({
        id: `temp_${Date.now()}_${Math.random()}`,
        name: file.name,
        size: file.size,
        type: file.type,
        url: '',
        uploadedBy: {
          id: 0,
          name: '当前用户'
        },
        uploadedAt: new Date().toISOString(),
        downloadCount: 0,
        isPublic: false,
        status: 'uploading',
        uploadProgress: 0,
        permissions: {
          canDownload: true,
          canDelete: true,
          canShare: true
        }
      }))

      // 添加临时文件到列表
      setFiles(prev => [...prev, ...tempFiles])

      // 上传文件
      const uploadedFiles = await fileService.uploadFiles(
        fileList,
        uploadOptions,
        (fileId, progress) => {
          setUploadProgress(prev => ({
            ...prev,
            [fileId]: progress
          }))

          // 更新临时文件的进度
          setFiles(prev => prev.map(file => {
            if (file.id === fileId) {
              return { ...file, uploadProgress: progress }
            }
            return file
          }))
        }
      )

      // 移除临时文件，添加真实文件
      setFiles(prev => {
        const withoutTemp = prev.filter(file => !file.id.startsWith('temp_'))
        return [...withoutTemp, ...uploadedFiles]
      })

      // 清理上传进度
      setUploadProgress({})

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '文件上传失败'
      setError(errorMessage)
      console.error('文件上传失败:', err)

      // 移除失败的临时文件
      setFiles(prev => prev.filter(file => !file.id.startsWith('temp_')))
    } finally {
      setUploading(false)
    }
  }, [meetingId, maxFileSize, allowedTypes])

  // 下载文件
  const downloadFile = useCallback(async (fileId: string) => {
    try {
      await fileService.downloadFile(fileId)
      
      // 更新文件的下载统计
      setFiles(prev => prev.map(file => 
        file.id === fileId 
          ? { ...file, downloadCount: file.downloadCount + 1 }
          : file
      ))
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '文件下载失败'
      setError(errorMessage)
      console.error('文件下载失败:', err)
    }
  }, [])

  // 删除文件
  const deleteFile = useCallback(async (fileId: string) => {
    try {
      await fileService.deleteFile(fileId)
      
      // 从列表中移除文件
      setFiles(prev => prev.filter(file => file.id !== fileId))
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '文件删除失败'
      setError(errorMessage)
      console.error('文件删除失败:', err)
    }
  }, [])

  // 分享文件
  const shareFile = useCallback(async (fileId: string, options: {
    expiresAt?: string
    password?: string
    allowDownload?: boolean
  } = {}) => {
    try {
      const result = await fileService.shareFile(fileId, options)
      
      // 复制分享链接到剪贴板
      await navigator.clipboard.writeText(result.shareUrl)
      
      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '文件分享失败'
      setError(errorMessage)
      console.error('文件分享失败:', err)
      throw err
    }
  }, [])

  // 搜索文件
  const searchFiles = useCallback(async (query: string, filters?: {
    type?: string
    uploadedBy?: number
    dateRange?: { start: string; end: string }
  }) => {
    if (!meetingId) return []

    try {
      const results = await fileService.searchFiles(meetingId, query, filters)
      return results
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '搜索文件失败'
      setError(errorMessage)
      console.error('搜索文件失败:', err)
      return []
    }
  }, [meetingId])

  // 获取文件统计
  const getFileStats = useCallback(async (fileId: string) => {
    try {
      return await fileService.getFileStats(fileId)
    } catch (err) {
      console.error('获取文件统计失败:', err)
      return null
    }
  }, [])

  // 检查文件权限
  const checkPermission = useCallback(async (fileId: string, action: 'download' | 'delete' | 'share') => {
    try {
      return await fileService.checkFilePermission(fileId, action)
    } catch (err) {
      console.error('检查文件权限失败:', err)
      return false
    }
  }, [])

  // 清除错误
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  // 刷新文件列表
  const refreshFiles = useCallback(() => {
    fetchFiles()
  }, [fetchFiles])

  // 初始化加载
  useEffect(() => {
    if (meetingId) {
      fetchFiles()
    }
  }, [meetingId, fetchFiles])

  // 自动刷新
  useEffect(() => {
    if (!autoRefresh || !meetingId) return

    const interval = setInterval(() => {
      fetchFiles()
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefresh, meetingId, refreshInterval, fetchFiles])

  // 计算统计信息
  const stats = {
    totalFiles: files.length,
    totalSize: files.reduce((sum, file) => sum + file.size, 0),
    totalDownloads: files.reduce((sum, file) => sum + file.downloadCount, 0),
    readyFiles: files.filter(f => f.status === 'ready').length,
    uploadingFiles: files.filter(f => f.status === 'uploading').length,
    errorFiles: files.filter(f => f.status === 'error').length
  }

  return {
    // 数据
    files,
    stats,
    
    // 状态
    loading,
    uploading,
    uploadProgress,
    error,
    
    // 操作
    uploadFiles,
    downloadFile,
    deleteFile,
    shareFile,
    searchFiles,
    getFileStats,
    checkPermission,
    refreshFiles,
    clearError,
    
    // 工具函数
    formatFileSize: fileService.formatFileSize,
    getFileIconType: fileService.getFileIconType,
    canPreviewFile: fileService.canPreviewFile,
    validateFile: (file: File) => fileService.validateFile(file, {
      maxSize: maxFileSize,
      allowedTypes
    })
  }
}

export default useFileShare