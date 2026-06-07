// 文件服务
import { api } from './api'

export interface SharedFile {
  id: string
  name: string
  size: number
  type: string
  url: string
  thumbnailUrl?: string
  uploadedBy: {
    id: number
    name: string
    avatar?: string
  }
  uploadedAt: string
  downloadCount: number
  isPublic: boolean
  description?: string
  tags?: string[]
  status: 'uploading' | 'processing' | 'ready' | 'error'
  uploadProgress?: number
  permissions?: {
    canDownload: boolean
    canDelete: boolean
    canShare: boolean
  }
}

export interface FileUploadOptions {
  meetingId: number
  isPublic?: boolean
  description?: string
  tags?: string[]
}

export interface FileShareOptions {
  expiresAt?: string
  password?: string
  allowDownload?: boolean
}

class FileService {
  // 获取会议文件列表
  async getMeetingFiles(meetingId: number): Promise<SharedFile[]> {
    try {
      const response = await api.get(`/meetings/${meetingId}/files`)
      return response.data
    } catch (error) {
      console.error('获取文件列表失败:', error)
      throw error
    }
  }

  // 上传文件
  async uploadFile(
    file: File, 
    options: FileUploadOptions,
    onProgress?: (progress: number) => void
  ): Promise<SharedFile> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('meetingId', options.meetingId.toString())
      
      if (options.isPublic !== undefined) {
        formData.append('isPublic', options.isPublic.toString())
      }
      
      if (options.description) {
        formData.append('description', options.description)
      }
      
      if (options.tags) {
        formData.append('tags', JSON.stringify(options.tags))
      }

      const response = await api.post(`/meetings/${options.meetingId}/files/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total && onProgress) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            onProgress(progress)
          }
        }
      })

      return response.data
    } catch (error) {
      console.error('文件上传失败:', error)
      throw error
    }
  }

  // 批量上传文件
  async uploadFiles(
    files: FileList,
    options: FileUploadOptions,
    onProgress?: (fileId: string, progress: number) => void
  ): Promise<SharedFile[]> {
    const uploadPromises = Array.from(files).map(async (file) => {
      const fileId = `temp_${Date.now()}_${Math.random()}`
      
      try {
        return await this.uploadFile(file, options, (progress) => {
          onProgress?.(fileId, progress)
        })
      } catch (error) {
        console.error(`文件 ${file.name} 上传失败:`, error)
        throw error
      }
    })

    return Promise.all(uploadPromises)
  }

  // 下载文件
  async downloadFile(fileId: string): Promise<void> {
    try {
      const response = await api.get(`/files/${fileId}/download`, {
        responseType: 'blob'
      })

      // 创建下载链接
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // 从响应头获取文件名
      const contentDisposition = response.headers['content-disposition']
      let filename = 'download'
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      // 更新下载统计
      await this.updateDownloadCount(fileId)
    } catch (error) {
      console.error('文件下载失败:', error)
      throw error
    }
  }

  // 删除文件
  async deleteFile(fileId: string): Promise<void> {
    try {
      await api.delete(`/files/${fileId}`)
    } catch (error) {
      console.error('文件删除失败:', error)
      throw error
    }
  }

  // 分享文件
  async shareFile(fileId: string, options: FileShareOptions = {}): Promise<{ shareUrl: string; shareId: string }> {
    try {
      const response = await api.post(`/files/${fileId}/share`, options)
      return response.data
    } catch (error) {
      console.error('文件分享失败:', error)
      throw error
    }
  }

  // 获取文件预览信息
  async getFilePreview(fileId: string): Promise<{ previewUrl: string; type: string }> {
    try {
      const response = await api.get(`/files/${fileId}/preview`)
      return response.data
    } catch (error) {
      console.error('获取文件预览失败:', error)
      throw error
    }
  }

  // 更新下载统计
  private async updateDownloadCount(fileId: string): Promise<void> {
    try {
      await api.post(`/files/${fileId}/download-count`)
    } catch (error) {
      console.error('更新下载统计失败:', error)
      // 不抛出错误，因为这不是关键操作
    }
  }

  // 获取文件访问统计
  async getFileStats(fileId: string): Promise<{
    downloadCount: number
    viewCount: number
    shareCount: number
    lastAccessed: string
  }> {
    try {
      const response = await api.get(`/files/${fileId}/stats`)
      return response.data
    } catch (error) {
      console.error('获取文件统计失败:', error)
      throw error
    }
  }

  // 检查文件权限
  async checkFilePermission(fileId: string, action: 'download' | 'delete' | 'share'): Promise<boolean> {
    try {
      const response = await api.get(`/files/${fileId}/permissions/${action}`)
      return response.data.allowed
    } catch (error) {
      console.error('检查文件权限失败:', error)
      return false
    }
  }

  // 搜索文件
  async searchFiles(meetingId: number, query: string, filters?: {
    type?: string
    uploadedBy?: number
    dateRange?: { start: string; end: string }
  }): Promise<SharedFile[]> {
    try {
      const params = new URLSearchParams()
      params.append('q', query)
      
      if (filters?.type) {
        params.append('type', filters.type)
      }
      
      if (filters?.uploadedBy) {
        params.append('uploadedBy', filters.uploadedBy.toString())
      }
      
      if (filters?.dateRange) {
        params.append('startDate', filters.dateRange.start)
        params.append('endDate', filters.dateRange.end)
      }

      const response = await api.get(`/meetings/${meetingId}/files/search?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('搜索文件失败:', error)
      throw error
    }
  }

  // 获取文件类型统计
  async getFileTypeStats(meetingId: number): Promise<{
    [type: string]: { count: number; totalSize: number }
  }> {
    try {
      const response = await api.get(`/meetings/${meetingId}/files/stats/types`)
      return response.data
    } catch (error) {
      console.error('获取文件类型统计失败:', error)
      throw error
    }
  }

  // 验证文件类型和大小
  validateFile(file: File, options: {
    maxSize?: number // MB
    allowedTypes?: string[]
  } = {}): { valid: boolean; error?: string } {
    const { maxSize = 100, allowedTypes = ['*'] } = options

    // 检查文件大小
    if (file.size > maxSize * 1024 * 1024) {
      return {
        valid: false,
        error: `文件大小不能超过 ${maxSize}MB`
      }
    }

    // 检查文件类型
    if (allowedTypes.length > 0 && !allowedTypes.includes('*')) {
      const isAllowed = allowedTypes.some(type => 
        file.type.includes(type) || file.name.toLowerCase().endsWith(type)
      )
      
      if (!isAllowed) {
        return {
          valid: false,
          error: `不支持的文件类型: ${file.type}`
        }
      }
    }

    return { valid: true }
  }

  // 格式化文件大小
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // 获取文件图标类型
  getFileIconType(mimeType: string): 'image' | 'video' | 'audio' | 'document' | 'archive' | 'code' | 'file' {
    if (mimeType.startsWith('image/')) return 'image'
    if (mimeType.startsWith('video/')) return 'video'
    if (mimeType.startsWith('audio/')) return 'audio'
    if (mimeType.includes('pdf') || mimeType.includes('document') || mimeType.includes('text/')) return 'document'
    if (mimeType.includes('zip') || mimeType.includes('rar') || mimeType.includes('tar')) return 'archive'
    if (mimeType.includes('javascript') || mimeType.includes('json') || mimeType.includes('xml')) return 'code'
    return 'file'
  }

  // 检查文件是否可以预览
  canPreviewFile(mimeType: string): boolean {
    return mimeType.startsWith('image/') || 
           mimeType.includes('pdf') || 
           mimeType.startsWith('text/') ||
           mimeType.includes('json') ||
           mimeType.includes('xml')
  }
}

export const fileService = new FileService()
export default fileService