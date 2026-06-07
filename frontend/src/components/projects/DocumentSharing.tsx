import React, { useMemo, useState } from 'react'
import { Download, FileText, Search, Upload } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import type { ProjectDocument } from '@/types/project'

interface DocumentSharingProps {
  projectId: number
  documents?: ProjectDocument[]
  onUpload?: () => void
  onDownload?: (document: ProjectDocument) => void
  onPreview?: (document: ProjectDocument) => void
  className?: string
}

const statusText: Record<ProjectDocument['status'], string> = {
  draft: '草稿',
  review: '评审中',
  approved: '已批准',
  archived: '已归档',
}

export const DocumentSharing: React.FC<DocumentSharingProps> = ({
  projectId,
  documents = [],
  onUpload,
  onDownload,
  onPreview,
  className = '',
}) => {
  const [keyword, setKeyword] = useState('')
  const filteredDocuments = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    if (!normalized) return documents
    return documents.filter((document) =>
      [document.name, document.description, document.file_type]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalized)),
    )
  }, [documents, keyword])

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">项目文档</CardTitle>
        <Button type="button" onClick={onUpload}>
          <Upload className="mr-2 h-4 w-4" />
          上传文档
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索文档"
            className="pl-9"
          />
        </div>

        {filteredDocuments.length === 0 ? (
          <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">
            项目 #{projectId} 暂无共享文档。
          </div>
        ) : (
          <div className="space-y-2">
            {filteredDocuments.map((document) => (
              <div key={document.id} className="flex items-center justify-between gap-3 rounded-md border p-3">
                <button type="button" className="flex min-w-0 items-center gap-3 text-left" onClick={() => onPreview?.(document)}>
                  <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{document.name}</span>
                    <span className="block text-xs text-muted-foreground">
                      {document.file_type} · v{document.version} · {Math.round((document.file_size || 0) / 1024)} KB
                    </span>
                  </span>
                </button>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge variant="outline">{statusText[document.status] || document.status}</Badge>
                  <Button type="button" variant="ghost" size="sm" onClick={() => onDownload?.(document)}>
                    <Download className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default DocumentSharing
