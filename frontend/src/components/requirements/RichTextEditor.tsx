import React, { useState, useRef } from 'react'
import { 
  Bold, 
  Italic, 
  Underline, 
  List, 
  ListOrdered,
  Link,
  Quote,
  Code,
  Undo,
  Redo,
  Eye,
  Edit
} from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import { Separator } from '@/components/ui/Separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'

interface RichTextEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  rows?: number
  className?: string
}

export const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  placeholder = "请输入内容...",
  rows = 8,
  className
}) => {
  const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 插入文本到光标位置
  const insertText = (before: string, after: string = '') => {
    const textarea = textareaRef.current
    if (!textarea) return

    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const selectedText = value.substring(start, end)
    
    const newText = value.substring(0, start) + before + selectedText + after + value.substring(end)
    onChange(newText)

    // 恢复光标位置
    setTimeout(() => {
      textarea.focus()
      textarea.setSelectionRange(start + before.length, end + before.length)
    }, 0)
  }

  // 格式化按钮处理
  const handleFormat = (type: string) => {
    switch (type) {
      case 'bold':
        insertText('**', '**')
        break
      case 'italic':
        insertText('*', '*')
        break
      case 'underline':
        insertText('<u>', '</u>')
        break
      case 'code':
        insertText('`', '`')
        break
      case 'quote':
        insertText('> ')
        break
      case 'list':
        insertText('- ')
        break
      case 'ordered-list':
        insertText('1. ')
        break
      case 'link':
        insertText('[链接文本](', ')')
        break
      default:
        break
    }
  }

  // 渲染Markdown预览
  const renderPreview = (text: string) => {
    // 简单的Markdown渲染（实际项目中建议使用专业的Markdown解析库）
    let html = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/<u>(.*?)<\/u>/g, '<u>$1</u>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/^(\d+)\. (.+)$/gm, '<li>$1. $2</li>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      .replace(/\n/g, '<br>')

    // 包装列表项
    html = html.replace(/(<li>.*<\/li>)/g, '<ul>$1</ul>')

    return html
  }

  return (
    <div className={`border rounded-lg ${className}`}>
      {/* 工具栏 */}
      <div className="flex items-center justify-between p-2 border-b bg-muted/50">
        <div className="flex items-center space-x-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleFormat('bold')}
            title="粗体"
          >
            <Bold className="w-4 h-4" />
          </Button>
          
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleFormat('italic')}
            title="斜体"
          >
            <Italic className="w-4 h-4" />
          </Button>
          
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleFormat('underline')}
            title="下划线"
          >
            <Underline className="w-4 h-4" />
          </Button>

          <Separator orientation="vertical" className="h-6" />
          
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleFormat('list')}
            title="无序列表"
          >
            <List className="w-4 h-4" />
          </Button>
          
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleFormat('ordered-list')}
            title="有序列表"
          >
            <ListOrdered className="w-4 h-4" />
          </Button>

          <Separator orientation="vertical" className="h-6" />
          
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleFormat('quote')}
            title="引用"
          >
            <Quote className="w-4 h-4" />
          </Button>
          
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleFormat('code')}
            title="代码"
          >
            <Code className="w-4 h-4" />
          </Button>
          
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => handleFormat('link')}
            title="链接"
          >
            <Link className="w-4 h-4" />
          </Button>
        </div>

        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'edit' | 'preview')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="edit" className="flex items-center space-x-1">
              <Edit className="w-3 h-3" />
              <span>编辑</span>
            </TabsTrigger>
            <TabsTrigger value="preview" className="flex items-center space-x-1">
              <Eye className="w-3 h-3" />
              <span>预览</span>
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* 编辑器内容 */}
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'edit' | 'preview')}>
        <TabsContent value="edit" className="m-0">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            rows={rows}
            className="border-0 rounded-none resize-none focus:ring-0"
          />
        </TabsContent>
        
        <TabsContent value="preview" className="m-0">
          <div 
            className="p-4 min-h-[200px] prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: renderPreview(value) }}
          />
        </TabsContent>
      </Tabs>

      {/* 底部提示 */}
      <div className="px-3 py-2 text-xs text-muted-foreground border-t bg-muted/25">
        支持 Markdown 语法：**粗体** *斜体* `代码` &gt; 引用 - 列表 [链接](URL)
      </div>
    </div>
  )
}

export default RichTextEditor