// 文件共享组件
import React, { useState, useRef, useCallback, useMemo } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
// Simple Badge component inline
const Badge: React.FC<{ children: React.ReactNode; variant?: 'default' | 'outline' | 'secondary'; className?: string }> = ({ 
  children, 
  variant = 'default', 
  className = '' 
}) => {
  const baseClasses = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold'
  const variantClasses = {
    default: 'bg-primary text-primary-foreground',
    outline: 'border border-input bg-background',
    secondary: 'bg-secondary text-secondary-foreground'
  }
  
  return (
    <div className={cn(baseClasses, variantClasses[variant], className)}>
      {children}
    </div>
  )
}
import { Progress } from '@/components/ui/Progress'
import { ScrollArea } from '@/components/ui/ScrollArea'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '@/components/ui/DropdownMenu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/Dialog'
import { 
  Upload,
  Download,
  File,
  Image as ImageIcon,
  Video,
  Music,
  FileText,
  Archive,
  Code,
  Search,
  MoreVertical,
  Trash2,
  Share,
  Eye,
  Copy,
  Clock,
  User,
  CheckCircle,
  AlertCircle,
  X,
  Paperclip,
  FolderOpen,
  Grid,
  List
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

import { useFileShare } from '@/hooks/meeting/useFileShare'
import type { SharedFile } from '@/services/fileService'

interface FileShareProps {
  meetingId?: number
  currentUserId?: number
  maxFileSize?: number // MB
  allowedTypes?: string[]
  className?: string
}

interface FileItemProps {
  file: SharedFile
  currentUserId?: number
  viewMode: 'grid' | 'list'
  onDownload?: (fileId: string) => void
  onDelete?: (fileId: string) => void
  onShare?: (fileId: string) => void
  onPreview?: (file: SharedFile) => void
  formatFileSize: (bytes: number) => string
  getFileIconType: (mimeType: string) => string
}

// 单个文件项组件
const FileItem: React.FC<FileItemProps> = ({
  file,
  currentUserId,
  viewMode,
  onDownload,
  onDelete,
  onShare,
  onPreview,
  formatFileSize,
  getFileIconType
}) => {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  // 获取文件图标
  const getFileIcon = (type: string, size: number = 24) => {
    const iconClass = `h-${size/4} w-${size/4}`
    const iconType = getFileIconType(type)
    
    switch (iconType) {
      case 'image': return <ImageIcon className={iconClass} />
      case 'video': return <Video className={iconClass} />
      case 'audio': return <Music className={iconClass} />
      case 'document': return <FileText className={iconClass} />
      case 'archive': return <Archive className={iconClass} />
      case 'code': return <Code className={iconClass} />
      default: return <File className={iconClass} />
    }
  }

  // 格式化时间
  const formatTime = (timestamp: string) => {
    return formatDistanceToNow(new Date(timestamp), { 
      addSuffix: true, 
      locale: zhCN 
    })
  }

  // 获取状态图标
  const getStatusIcon = () => {
    switch (file.status) {
      case 'uploading':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin dark:text-blue-400" />
      case 'processing':
        return <Clock className="h-4 w-4 text-yellow-500" />
      case 'ready':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500 dark:text-red-400" />
      default:
        return null
    }
  }

  // 是否可以预览
  const canPreview = file.type.startsWith('image/') || 
                    file.type.includes('pdf') || 
                    file.type.startsWith('text/')

  // 网格视图
  if (viewMode === 'grid') {
    return (
      <div className="group relative bg-card border rounded-lg p-4 hover:shadow-md transition-shadow">
        {/* 文件预览/图标 */}
        <div className="flex items-center justify-center h-20 mb-3">
          {file.thumbnailUrl ? (
            <img 
              src={file.thumbnailUrl} 
              alt={file.name}
              className="max-h-full max-w-full object-contain rounded"
            />
          ) : (
            getFileIcon(file.type, 48)
          )}
        </div>

        {/* 文件信息 */}
        <div className="space-y-2">
          <h4 className="font-medium text-sm truncate" title={file.name}>
            {file.name}
          </h4>
          
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{formatFileSize(file.size)}</span>
            {getStatusIcon()}
          </div>

          <div className="flex items-center space-x-1 text-xs text-muted-foreground">
            <User className="h-3 w-3" />
            <span className="truncate">{file.uploadedBy.name}</span>
          </div>

          {/* 上传进度 */}
          {file.status === 'uploading' && file.uploadProgress !== undefined && (
            <Progress value={file.uploadProgress} className="h-1" />
          )}
        </div>

        {/* 操作按钮 */}
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="ghost" className="h-6 w-6 p-0">
                <MoreVertical className="h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {canPreview && (
                <DropdownMenuItem onClick={() => onPreview?.(file)}>
                  <Eye className="h-4 w-4 mr-2" />
                  预览
                </DropdownMenuItem>
              )}
              
              {file.permissions?.canDownload && (
                <DropdownMenuItem onClick={() => onDownload?.(file.id)}>
                  <Download className="h-4 w-4 mr-2" />
                  下载
                </DropdownMenuItem>
              )}
              
              {file.permissions?.canShare && (
                <DropdownMenuItem onClick={() => onShare?.(file.id)}>
                  <Share className="h-4 w-4 mr-2" />
                  分享
                </DropdownMenuItem>
              )}
              
              <DropdownMenuItem onClick={() => navigator.clipboard.writeText(file.url)}>
                <Copy className="h-4 w-4 mr-2" />
                复制链接
              </DropdownMenuItem>

              {file.permissions?.canDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    onClick={() => setShowDeleteDialog(true)}
                    className="text-destructive"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    删除
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* 删除确认对话框 */}
        <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>删除文件</DialogTitle>
              <DialogDescription>
                确定要删除文件 "{file.name}" 吗？此操作无法撤销。
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
                取消
              </Button>
              <Button 
                variant="destructive" 
                onClick={() => {
                  onDelete?.(file.id)
                  setShowDeleteDialog(false)
                }}
              >
                删除
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    )
  }

  // 列表视图
  return (
    <div className="group flex items-center space-x-3 p-3 hover:bg-accent/50 rounded-lg transition-colors">
      {/* 文件图标 */}
      <div className="flex-shrink-0">
        {file.thumbnailUrl ? (
          <img 
            src={file.thumbnailUrl} 
            alt={file.name}
            className="h-10 w-10 object-cover rounded"
          />
        ) : (
          getFileIcon(file.type, 40)
        )}
      </div>

      {/* 文件信息 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2">
          <h4 className="font-medium text-sm truncate">{file.name}</h4>
          {getStatusIcon()}
          
          {file.isPublic && (
            <Badge variant="outline" className="text-xs">公开</Badge>
          )}
        </div>
        
        <div className="flex items-center space-x-4 mt-1 text-xs text-muted-foreground">
          <span>{formatFileSize(file.size)}</span>
          <span>•</span>
          <span>{file.uploadedBy.name}</span>
          <span>•</span>
          <span>{formatTime(file.uploadedAt)}</span>
          <span>•</span>
          <span>{file.downloadCount} 次下载</span>
        </div>

        {/* 上传进度 */}
        {file.status === 'uploading' && file.uploadProgress !== undefined && (
          <Progress value={file.uploadProgress} className="h-1 mt-2" />
        )}
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {canPreview && (
          <Button size="sm" variant="ghost" onClick={() => onPreview?.(file)}>
            <Eye className="h-4 w-4" />
          </Button>
        )}
        
        {file.permissions?.canDownload && (
          <Button size="sm" variant="ghost" onClick={() => onDownload?.(file.id)}>
            <Download className="h-4 w-4" />
          </Button>
        )}
        
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button size="sm" variant="ghost">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {file.permissions?.canShare && (
              <DropdownMenuItem onClick={() => onShare?.(file.id)}>
                <Share className="h-4 w-4 mr-2" />
                分享
              </DropdownMenuItem>
            )}
            
            <DropdownMenuItem onClick={() => navigator.clipboard.writeText(file.url)}>
              <Copy className="h-4 w-4 mr-2" />
              复制链接
            </DropdownMenuItem>

            {file.permissions?.canDelete && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  onClick={() => setShowDeleteDialog(true)}
                  className="text-destructive"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  删除
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* 删除确认对话框 */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除文件</DialogTitle>
            <DialogDescription>
              确定要删除文件 "{file.name}" 吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              取消
            </Button>
            <Button 
              variant="destructive" 
              onClick={() => {
                onDelete?.(file.id)
                setShowDeleteDialog(false)
              }}
            >
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// 主文件共享组件
const FileShare: React.FC<FileShareProps> = ({
  meetingId,
  currentUserId = 1,
  maxFileSize = 100, // 100MB
  allowedTypes = ['*'],
  className
}) => {
  // 使用文件共享Hook
  const {
    files,
    stats,
    loading,
    uploading,
    error,
    uploadFiles,
    downloadFile,
    deleteFile,
    shareFile,
    clearError,
    formatFileSize,
    getFileIconType
  } = useFileShare({
    meetingId,
    maxFileSize,
    allowedTypes,
    autoRefresh: true,
    refreshInterval: 30000
  })

  // 状态管理
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list')
  const [filterType, setFilterType] = useState<string>('all')
  const [dragOver, setDragOver] = useState(false)
  const [previewFile, setPreviewFile] = useState<SharedFile | null>(null)

  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dropZoneRef = useRef<HTMLDivElement>(null)

  // 过滤文件
  const filteredFiles = useMemo(() => {
    return files.filter(file => {
      // 搜索过滤
      const matchesSearch = !searchQuery || 
        file.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        file.uploadedBy.name.toLowerCase().includes(searchQuery.toLowerCase())

      // 类型过滤
      const matchesType = filterType === 'all' || 
        (filterType === 'image' && file.type.startsWith('image/')) ||
        (filterType === 'video' && file.type.startsWith('video/')) ||
        (filterType === 'audio' && file.type.startsWith('audio/')) ||
        (filterType === 'document' && (file.type.includes('pdf') || file.type.includes('document'))) ||
        (filterType === 'archive' && (file.type.includes('zip') || file.type.includes('rar')))

      return matchesSearch && matchesType
    })
  }, [files, searchQuery, filterType])

  // 处理文件操作
  const handleDownload = useCallback((fileId: string) => {
    downloadFile(fileId)
  }, [downloadFile])

  const handleDelete = useCallback((fileId: string) => {
    deleteFile(fileId)
  }, [deleteFile])

  const handleShare = useCallback(async (fileId: string) => {
    try {
      await shareFile(fileId)
      // 显示成功消息
      alert('分享链接已复制到剪贴板')
    } catch (error) {
      console.error('分享失败:', error)
    }
  }, [shareFile])

  // 处理文件上传
  const handleFileUpload = useCallback((fileList: FileList) => {
    uploadFiles(fileList)
  }, [uploadFiles])

  // 拖拽处理
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileUpload(files)
    }
  }, [handleFileUpload])

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* 错误提示 */}
      {error && (
        <div className="p-4 bg-destructive/10 border-b border-destructive/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 text-destructive" />
              <span className="text-sm text-destructive">{error}</span>
            </div>
            <Button size="sm" variant="ghost" onClick={clearError}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* 头部 */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold">文件共享 ({stats.totalFiles})</h3>
          
          <div className="flex items-center space-x-2">
            {/* 视图切换 */}
            <Button
              size="sm"
              variant={viewMode === 'grid' ? 'default' : 'outline'}
              onClick={() => setViewMode('grid')}
            >
              <Grid className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'list' ? 'default' : 'outline'}
              onClick={() => setViewMode('list')}
            >
              <List className="h-4 w-4" />
            </Button>

            {/* 上传按钮 */}
            <Button 
              size="sm" 
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || !meetingId}
            >
              {uploading ? (
                <>
                  <Clock className="h-4 w-4 mr-1 animate-spin" />
                  上传中...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-1" />
                  上传
                </>
              )}
            </Button>
          </div>
        </div>

        {/* 统计信息 */}
        <div className="flex space-x-4 text-sm text-muted-foreground mb-3">
          <span>{stats.readyFiles} 个文件可用</span>
          <span>•</span>
          <span>总大小 {formatFileSize(stats.totalSize)}</span>
          <span>•</span>
          <span>{stats.totalDownloads} 次下载</span>
        </div>

        {/* 搜索和过滤 */}
        <div className="flex space-x-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索文件..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-2 text-sm border rounded-md"
          >
            <option value="all">所有类型</option>
            <option value="image">图片</option>
            <option value="video">视频</option>
            <option value="audio">音频</option>
            <option value="document">文档</option>
            <option value="archive">压缩包</option>
          </select>
        </div>
      </div>

      {/* 文件列表 */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="text-center">
              <Clock className="h-8 w-8 animate-spin mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">加载文件列表...</p>
            </div>
          </div>
        ) : filteredFiles.length === 0 ? (
          // 空状态/拖拽区域
          <div
            ref={dropZoneRef}
            className={cn(
              "h-full flex items-center justify-center border-2 border-dashed rounded-lg m-4 transition-colors",
              dragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25"
            )}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="text-center">
              <FolderOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">
                {files.length === 0 ? '暂无文件' : '未找到匹配的文件'}
              </h3>
              <p className="text-muted-foreground mb-4">
                {files.length === 0 
                  ? '拖拽文件到此处或点击上传按钮开始分享文件'
                  : '尝试调整搜索条件或文件类型过滤器'
                }
              </p>
              {files.length === 0 && (
                <Button onClick={() => fileInputRef.current?.click()}>
                  <Upload className="h-4 w-4 mr-2" />
                  选择文件
                </Button>
              )}
            </div>
          </div>
        ) : (
          <ScrollArea className="h-full">
            <div className={cn(
              "p-4",
              viewMode === 'grid' 
                ? "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
                : "space-y-1"
            )}>
              {filteredFiles.map(file => (
                <FileItem
                  key={file.id}
                  file={file}
                  currentUserId={currentUserId}
                  viewMode={viewMode}
                  onDownload={handleDownload}
                  onDelete={handleDelete}
                  onShare={handleShare}
                  onPreview={setPreviewFile}
                  formatFileSize={formatFileSize}
                  getFileIconType={getFileIconType}
                />
              ))}
            </div>
          </ScrollArea>
        )}
      </div>

      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
        accept={allowedTypes.includes('*') ? undefined : allowedTypes.join(',')}
      />

      {/* 文件预览对话框 */}
      {previewFile && (
        <Dialog open={!!previewFile} onOpenChange={() => setPreviewFile(null)}>
          <DialogContent className="max-w-4xl max-h-[80vh]">
            <DialogHeader>
              <DialogTitle>
                <div className="flex items-center space-x-2">
                  {previewFile.type.startsWith('image/') ? (
                    <ImageIcon className="h-5 w-5" />
                  ) : (
                    <FileText className="h-5 w-5" />
                  )}
                  <span>{previewFile.name}</span>
                </div>
              </DialogTitle>
              <DialogDescription>
                {formatFileSize(previewFile.size)} • 
                上传者: {previewFile.uploadedBy.name} • 
                {previewFile.downloadCount} 次下载
              </DialogDescription>
            </DialogHeader>

            <div className="flex-1 overflow-auto">
              {previewFile.type.startsWith('image/') ? (
                <img 
                  src={previewFile.url} 
                  alt={previewFile.name}
                  className="max-w-full h-auto mx-auto"
                />
              ) : previewFile.type.includes('pdf') ? (
                <iframe 
                  src={previewFile.url}
                  className="w-full h-96 border rounded"
                  title={previewFile.name}
                />
              ) : (
                <div className="text-center py-8">
                  <File className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">无法预览此文件类型</p>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setPreviewFile(null)}>
                关闭
              </Button>
              <Button onClick={() => handleDownload(previewFile.id)}>
                <Download className="h-4 w-4 mr-2" />
                下载
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}

export default FileShare