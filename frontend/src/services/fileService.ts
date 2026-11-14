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


// 后端 FileShareResponse -> 前端 SharedFile 的字段映射。
// 注意：services/api.ts 的响应拦截器已把 response.data 解包成 body，
// 所以这里收到的就是 body 本身，不能再取 .data。
function toSharedFile(f: any): SharedFile {
  return {
    id: String(f.id),
    name: f.file_name,
    size: f.file_size ?? 0,
    type: f.mime_type || f.file_type || '',
    url: f.download_url || f.preview_url || '',
    thumbnailUrl: f.preview_url,
    uploadedBy: {
      id: f.uploader_id ?? 0,
      name: f.uploader_name || '未知用户',
    },
    uploadedAt: f.uploaded_at,
    downloadCount: f.download_count ?? 0,
    isPublic: Boolean(f.is_public),
    description: f.description,
    status: f.status === 'AVAILABLE' ? 'ready' : 'error',
    permissions: {
      canDownload: true,
      canDelete: true,
      canShare: true,
    },
  }
}

class FileService {
  // 获取会议文件列表
  async getMeetingFiles(meetingId: number): Promise<SharedFile[]> {
    try {
      const body: any = await api.get(`/meetings/${meetingId}/files`)
      const files = body?.files ?? body?.data?.files ?? []
      return files.map(toSharedFile)
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

      const body: any = await api.post(`/meetings/${options.meetingId}/files/upload`, formData, {
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

      return toSharedFile(body?.data ?? body)
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
    // 后端没有 GET /files/{id}/download，见 fileService 头注。
    throw new Error('后端暂无该接口（会议文件目前只支持列表与上传）')
  }

  // 删除文件
  async deleteFile(fileId: string): Promise<void> {
    // 后端没有 DELETE /files/{id}，见 fileService 头注。
    throw new Error('后端暂无该接口（会议文件目前只支持列表与上传）')
  }

  // 分享文件
  async shareFile(fileId: string, options: FileShareOptions = {}): Promise<{ shareUrl: string; shareId: string }> {
    // 后端没有 POST /files/{id}/share，见 fileService 头注。
    throw new Error('后端暂无该接口（会议文件目前只支持列表与上传）')
  }


  // 获取文件预览信息
  async getFilePreview(fileId: string): Promise<{ previewUrl: string; type: string }> {
    // 后端没有 GET /files/{id}/preview，见 fileService 头注。
    throw new Error('后端暂无该接口（会议文件目前只支持列表与上传）')
  }


  // 更新下载统计
  private async updateDownloadCount(fileId: string): Promise<void> {
    // 后端没有 POST /files/{id}/download-count；下载统计随列表返回，
    // 这里直接跳过，不发无效请求。
    return
  }

  // 获取文件访问统计
  async getFileStats(fileId: string): Promise<{
    downloadCount: number
    viewCount: number
    shareCount: number
    lastAccessed: string
  }> {
    // 后端没有 GET /files/{id}/stats，见 fileService 头注。
    throw new Error('后端暂无该接口（会议文件目前只支持列表与上传）')
  }


  // 检查文件权限
  async checkFilePermission(fileId: string, action: 'download' | 'delete' | 'share'): Promise<boolean> {
    // 后端没有 GET /files/{id}/permissions/{action}；列表返回的权限
    // 默认放行，不发无效请求。
    return true
  }

  // 搜索文件
  // 搜索文件
  async searchFiles(meetingId: number, query: string, filters?: {
    type?: string
    uploadedBy?: number
    dateRange?: { start: string; end: string }
  }): Promise<SharedFile[]> {
    // 后端没有 /meetings/{id}/files/search；列表页本地过滤即可。
    const files = await this.getMeetingFiles(meetingId)
    const q = query.toLowerCase()
    return files.filter((f) => f.name.toLowerCase().includes(q))
  }

  // 获取文件类型统计
  async getFileTypeStats(meetingId: number): Promise<{
    [type: string]: { count: number; totalSize: number }
  }> {
    // 后端没有 /meetings/{id}/files/stats/types；由列表本地汇总。
    const files = await this.getMeetingFiles(meetingId)
    const stats: { [type: string]: { count: number; totalSize: number } } = {}
    files.forEach((f) => {
      const key = f.type || 'unknown'
      stats[key] = stats[key] || { count: 0, totalSize: 0 }
      stats[key].count += 1
      stats[key].totalSize += f.size
    })
    return stats
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