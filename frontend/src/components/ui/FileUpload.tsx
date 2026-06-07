import * as React from 'react'
import { Upload, X, File, Image, FileText, Video, Music } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from './Button'
import { Progress } from './Progress'

export interface FileItem {
  id: string
  file: File
  name: string
  size: number
  type: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
  url?: string
  error?: string
}

export interface FileUploadProps {
  accept?: string
  multiple?: boolean
  maxSize?: number // bytes
  maxFiles?: number
  disabled?: boolean
  className?: string
  dragDropText?: string
  browseText?: string
  onFilesChange?: (files: FileItem[]) => void
  onUpload?: (files: FileItem[]) => Promise<void>
  showPreview?: boolean
  showProgress?: boolean
}

export function FileUpload({
  accept,
  multiple = false,
  maxSize = 10 * 1024 * 1024, // 10MB
  maxFiles = 5,
  disabled = false,
  className,
  dragDropText = '拖拽文件到此处或点击选择文件',
  browseText = '选择文件',
  onFilesChange,
  onUpload,
  showPreview = true,
  showProgress = true
}: FileUploadProps) {
  const [files, setFiles] = React.useState<FileItem[]>([])
  const [isDragOver, setIsDragOver] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const generateFileId = () => Math.random().toString(36).substr(2, 9)

  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) return <Image className="h-4 w-4" />
    if (type.startsWith('video/')) return <Video className="h-4 w-4" />
    if (type.startsWith('audio/')) return <Music className="h-4 w-4" />
    if (type.includes('text') || type.includes('document')) return <FileText className="h-4 w-4" />
    return <File className="h-4 w-4" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const validateFile = (file: File): string | null => {
    if (maxSize && file.size > maxSize) {
      return `文件大小不能超过 ${formatFileSize(maxSize)}`
    }
    return null
  }

  const processFiles = (fileList: FileList) => {
    const newFiles: FileItem[] = []
    
    Array.from(fileList).forEach(file => {
      if (files.length + newFiles.length >= maxFiles) {
        return
      }

      const error = validateFile(file)
      const fileItem: FileItem = {
        id: generateFileId(),
        file,
        name: file.name,
        size: file.size,
        type: file.type,
        status: error ? 'error' : 'pending',
        progress: 0,
        error
      }

      newFiles.push(fileItem)
    })

    const updatedFiles = [...files, ...newFiles]
    setFiles(updatedFiles)
    onFilesChange?.(updatedFiles)
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = event.target.files
    if (fileList) {
      processFiles(fileList)
    }
    // 清空input值，允许选择相同文件
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault()
    if (!disabled) {
      setIsDragOver(true)
    }
  }

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault()
    setIsDragOver(false)
    
    if (disabled) return

    const fileList = event.dataTransfer.files
    if (fileList) {
      processFiles(fileList)
    }
  }

  const removeFile = (id: string) => {
    const updatedFiles = files.filter(file => file.id !== id)
    setFiles(updatedFiles)
    onFilesChange?.(updatedFiles)
  }

  const handleUpload = async () => {
    if (!onUpload) return

    const pendingFiles = files.filter(file => file.status === 'pending')
    if (pendingFiles.length === 0) return

    // 更新状态为上传中
    setFiles(prev => prev.map(file => 
      file.status === 'pending' 
        ? { ...file, status: 'uploading' as const, progress: 0 }
        : file
    ))

    try {
      await onUpload(pendingFiles)
      
      // 上传成功
      setFiles(prev => prev.map(file => 
        file.status === 'uploading' 
          ? { ...file, status: 'success' as const, progress: 100 }
          : file
      ))
    } catch (error) {
      // 上传失败
      setFiles(prev => prev.map(file => 
        file.status === 'uploading' 
          ? { ...file, status: 'error' as const, error: '上传失败' }
          : file
      ))
    }
  }

  const hasValidFiles = files.some(file => file.status === 'pending' && !file.error)

  return (
    <div className={cn('w-full', className)}>
      {/* 拖拽上传区域 */}
      <div
        className={cn(
          'relative border-2 border-dashed rounded-lg p-6 text-center transition-colors',
          isDragOver 
            ? 'border-primary bg-primary/5' 
            : 'border-muted-foreground/25 hover:border-muted-foreground/50',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleFileSelect}
          disabled={disabled}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
        />
        
        <div className="flex flex-col items-center space-y-2">
          <Upload className="h-8 w-8 text-muted-foreground" />
          <div className="text-sm text-muted-foreground">
            {dragDropText}
          </div>
          <Button type="button" variant="outline" size="sm" disabled={disabled}>
            {browseText}
          </Button>
        </div>

        {accept && (
          <p className="text-xs text-muted-foreground mt-2">
            支持格式: {accept}
          </p>
        )}
        
        <p className="text-xs text-muted-foreground">
          最大文件大小: {formatFileSize(maxSize)} | 最多 {maxFiles} 个文件
        </p>
      </div>

      {/* 文件列表 */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map((fileItem) => (
            <div
              key={fileItem.id}
              className={cn(
                'flex items-center space-x-3 p-3 border rounded-lg',
                fileItem.status === 'error' && 'border-destructive bg-destructive/5',
                fileItem.status === 'success' && 'border-success bg-success/5',
                fileItem.status === 'uploading' && 'border-primary bg-primary/5'
              )}
            >
              {/* 文件图标 */}
              <div className="flex-shrink-0">
                {showPreview && fileItem.type.startsWith('image/') && fileItem.url ? (
                  <img 
                    src={fileItem.url} 
                    alt={fileItem.name}
                    className="h-10 w-10 object-cover rounded"
                  />
                ) : (
                  <div className="h-10 w-10 bg-muted rounded flex items-center justify-center">
                    {getFileIcon(fileItem.type)}
                  </div>
                )}
              </div>

              {/* 文件信息 */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{fileItem.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(fileItem.size)}
                </p>
                
                {/* 进度条 */}
                {showProgress && fileItem.status === 'uploading' && (
                  <Progress value={fileItem.progress} className="mt-1 h-1" />
                )}
                
                {/* 错误信息 */}
                {fileItem.error && (
                  <p className="text-xs text-destructive mt-1">{fileItem.error}</p>
                )}
              </div>

              {/* 状态和操作 */}
              <div className="flex items-center space-x-2">
                {fileItem.status === 'success' && (
                  <div className="text-success">
                    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
                
                {fileItem.status === 'error' && (
                  <div className="text-destructive">
                    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}

                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeFile(fileItem.id)}
                  disabled={fileItem.status === 'uploading'}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 上传按钮 */}
      {hasValidFiles && onUpload && (
        <div className="mt-4 flex justify-end">
          <Button onClick={handleUpload}>
            上传文件 ({files.filter(f => f.status === 'pending' && !f.error).length})
          </Button>
        </div>
      )}
    </div>
  )
}