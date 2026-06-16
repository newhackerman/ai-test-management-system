import React, { useRef, useState } from 'react'
import { AlertCircle, FileText, Upload } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog'

interface ImportUsersDialogProps {
  open: boolean
  onClose: () => void
  onImport: (file: File) => Promise<void>
  loading?: boolean
}

const allowedExtensions = ['.csv', '.xlsx']

export const ImportUsersDialog: React.FC<ImportUsersDialogProps> = ({ open, onClose, onImport, loading = false }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const reset = () => {
    setSelectedFile(null)
    setDragOver(false)
    setError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const handleFileSelect = (file: File) => {
    const lowerName = file.name.toLowerCase()
    if (!allowedExtensions.some((extension) => lowerName.endsWith(extension))) {
      setError('仅支持 CSV、XLSX 文件')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setError('文件大小不能超过 10MB')
      return
    }

    setError('')
    setSelectedFile(file)
  }

  const handleImport = async () => {
    if (!selectedFile) return
    await onImport(selectedFile)
    reset()
  }

  const downloadTemplate = () => {
    const csvContent = [
      'username,email,password,nickname,phone,role_codes',
      'demo_user,demo@example.com,Demo123!,演示用户,13800138000,SYSTEM_ADMIN',
      'tester_user,tester@example.com,Tester123!,测试人员,13800138001,TESTER',
    ].join('\n')
    const blob = new Blob([`\uFEFF${csvContent}`], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'user_import_template.csv'
    link.click()
    URL.revokeObjectURL(link.href)
  }

  if (!open) return null

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && handleClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>导入用户</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-md border border-blue-200 bg-blue-50 p-4 dark:bg-blue-900/20">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-5 w-5 text-blue-600 dark:text-blue-400" />
              <div className="text-sm text-blue-800 dark:text-blue-300">
                <div className="font-medium">文件格式要求</div>
                <div className="mt-1 space-y-1">
                  <p>必填列：username, email, password</p>
                  <p>可选列：nickname, phone, role_codes</p>
                  <p>多个角色用英文逗号分隔，例如 SYSTEM_ADMIN,TESTER</p>
                </div>
              </div>
            </div>
          </div>

          <div
            className={`rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
              dragOver ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 hover:border-gray-400 dark:border-gray-600'
            }`}
            onDrop={(event) => {
              event.preventDefault()
              setDragOver(false)
              const file = event.dataTransfer.files?.[0]
              if (file) handleFileSelect(file)
            }}
            onDragOver={(event) => {
              event.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={(event) => {
              event.preventDefault()
              setDragOver(false)
            }}
          >
            {selectedFile ? (
              <div className="space-y-2">
                <FileText className="mx-auto h-12 w-12 text-green-600" />
                <p className="font-medium text-green-800">{selectedFile.name}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                <Button variant="outline" size="sm" onClick={() => setSelectedFile(null)}>
                  重新选择
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <Upload className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
                <p className="text-gray-600 dark:text-gray-400">
                  拖拽文件到这里，或
                  <button type="button" className="ml-1 text-blue-600 underline dark:text-blue-400" onClick={() => fileInputRef.current?.click()}>
                    点击选择文件
                  </button>
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">支持 .csv、.xlsx</p>
              </div>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) handleFileSelect(file)
            }}
          />

          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

          <div className="text-center">
            <Button variant="outline" size="sm" onClick={downloadTemplate}>
              下载 CSV 模板
            </Button>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={handleClose} disabled={loading}>
              取消
            </Button>
            <Button onClick={handleImport} disabled={loading || !selectedFile}>
              {loading ? '导入中...' : '开始导入'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default ImportUsersDialog
