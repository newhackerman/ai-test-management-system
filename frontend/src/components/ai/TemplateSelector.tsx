// @ts-nocheck
import { useEffect, useState } from 'react'
import { Clock, Copy, Eye, MessageSquare, Search, Star, TrendingUp, Wand2, X } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useToast } from '@/hooks/useToast'
import { PromptTemplate, promptTemplateService } from '@/services/prompt-template-service'

interface TemplateSelectorProps {
  onSelectTemplate?: (template: PromptTemplate, renderedContent?: string) => void
  onClose?: () => void
  isOpen?: boolean
  className?: string
}

interface TemplatePreview {
  template: PromptTemplate
  renderedContent: string
  variables: Record<string, any>
}

const tabs = [
  { key: 'recent', label: '最近使用', icon: Clock },
  { key: 'popular', label: '热门', icon: TrendingUp },
  { key: 'featured', label: '精选', icon: Star },
  { key: 'all', label: '全部', icon: MessageSquare },
] as const

export function TemplateSelector({ onSelectTemplate, onClose, isOpen = true, className = '' }: TemplateSelectorProps) {
  const { toast } = useToast()
  const [templates, setTemplates] = useState<PromptTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [activeTab, setActiveTab] = useState<'recent' | 'popular' | 'featured' | 'all'>('recent')
  const [previewTemplate, setPreviewTemplate] = useState<TemplatePreview | null>(null)
  const [previewVariables, setPreviewVariables] = useState<Record<string, any>>({})
  const [categories, setCategories] = useState<any[]>([])

  const loadTemplates = async () => {
    setLoading(true)
    try {
      let response
      if (activeTab === 'recent') {
        response = await promptTemplateService.getMyTemplates({ page: 1, size: 20 })
      } else if (activeTab === 'popular') {
        response = await promptTemplateService.getTemplates({ sort_by: 'usage_count', sort_order: 'desc', page: 1, size: 20 })
      } else if (activeTab === 'featured') {
        response = await promptTemplateService.getTemplates({ is_featured: true, page: 1, size: 20 })
      } else {
        response = await promptTemplateService.searchTemplates({
          query: searchQuery || undefined,
          category: selectedCategory || undefined,
          page: 1,
          size: 20,
        })
      }

      setTemplates(response?.templates || [])
    } catch (error: any) {
      toast({ title: '加载失败', description: error?.message || '加载模板失败', variant: 'destructive' })
    } finally {
      setLoading(false)
    }
  }

  const loadCategories = async () => {
    try {
      setCategories(await promptTemplateService.getCategories())
    } catch (error) {
      console.error('Failed to load categories:', error)
    }
  }

  useEffect(() => {
    if (!isOpen) return
    loadCategories()
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return
    loadTemplates()
  }, [isOpen, activeTab, searchQuery, selectedCategory])

  const buildDefaultContext = (template: PromptTemplate) => ({
    ...(template.example_context || {}),
    ...(template.default_values || {}),
  })

  const handlePreviewTemplate = async (template: PromptTemplate) => {
    try {
      const context = buildDefaultContext(template)
      const renderResponse = await promptTemplateService.renderTemplate(template.id, context)
      setPreviewTemplate({ template, renderedContent: renderResponse.rendered_content, variables: context })
      setPreviewVariables(context)
    } catch (error: any) {
      toast({ title: '预览失败', description: error?.message || '无法预览模板', variant: 'destructive' })
    }
  }

  const handleApplyTemplate = async (template: PromptTemplate, customVariables?: Record<string, any>) => {
    try {
      let renderedContent = template.content
      const variables = template.variables || []

      if (customVariables || variables.length > 0) {
        const context = customVariables || previewVariables || buildDefaultContext(template)
        const renderResponse = await promptTemplateService.renderTemplate(template.id, context)
        renderedContent = renderResponse.rendered_content
      }

      await promptTemplateService.recordUsage(template.id, {
        template_id: template.id,
        ai_provider: 'unknown',
        use_case: 'chat_input',
        success: true,
        variable_values: customVariables || previewVariables,
      })

      onSelectTemplate?.(template, renderedContent)
      onClose?.()
      toast({ title: '模板已应用', description: `已将模板“${template.title}”应用到输入框`, variant: 'success' })
    } catch (error: any) {
      toast({ title: '应用失败', description: error?.message || '应用模板失败', variant: 'destructive' })
    }
  }

  const handleUpdatePreviewVariable = (name: string, value: any) => {
    const nextVariables = { ...previewVariables, [name]: value }
    setPreviewVariables(nextVariables)

    if (previewTemplate) {
      const renderedContent = promptTemplateService.previewTemplate(previewTemplate.template.content, nextVariables)
      setPreviewTemplate({ ...previewTemplate, renderedContent, variables: nextVariables })
    }
  }

  const handleQuickApply = (template: PromptTemplate) => {
    if (!template.variables || template.variables.length === 0) {
      handleApplyTemplate(template)
      return
    }
    handlePreviewTemplate(template)
  }

  if (!isOpen) return null

  return (
    <div className={`rounded-lg border border-gray-200 bg-white shadow-lg ${className} dark:bg-gray-800 dark:border-gray-700`}>
      <div className="flex items-center justify-between border-b p-4">
        <h3 className="text-lg font-semibold">选择提示词模板</h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex h-96">
        <div className="flex flex-1 flex-col border-r">
          <div className="space-y-3 border-b p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
              <Input placeholder="搜索模板..." value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} className="pl-10" />
            </div>

            <select
              value={selectedCategory}
              onChange={(event) => setSelectedCategory(event.target.value)}
              className="h-9 w-full rounded border border-gray-300 px-2 text-sm dark:border-gray-600"
            >
              <option value="">所有分类</option>
              {categories.map((category) => (
                <option key={category.value} value={category.value}>
                  {category.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex border-b">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex-1 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === tab.key ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-center gap-1">
                    <Icon className="h-4 w-4" />
                    {tab.label}
                  </div>
                </button>
              )
            })}
          </div>

          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex h-full items-center justify-center text-sm text-gray-500 dark:text-gray-400">
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 dark:border-gray-600" />
                加载中...
              </div>
            ) : templates.length === 0 ? (
              <div className="flex h-full items-center justify-center text-gray-400 dark:text-gray-500">
                <div className="text-center">
                  <MessageSquare className="mx-auto mb-2 h-8 w-8" />
                  <p className="text-sm">暂无模板</p>
                </div>
              </div>
            ) : (
              <div className="space-y-2 p-2">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    type="button"
                    className="group w-full rounded-lg border border-gray-200 p-3 text-left hover:bg-gray-50 dark:bg-gray-800/50 dark:hover:bg-gray-800 dark:border-gray-700"
                    onClick={() => handleQuickApply(template)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="mb-1 flex items-center gap-2">
                          <h4 className="truncate text-sm font-medium">{template.title}</h4>
                          {template.is_featured && (
                            <Badge variant="outline" className="bg-yellow-100 text-yellow-800">
                              精选
                            </Badge>
                          )}
                        </div>
                        <p className="mb-2 line-clamp-2 text-xs text-gray-600 dark:text-gray-400">{template.description}</p>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline">{categories.find((item) => item.value === template.category)?.label || template.category}</Badge>
                          {(template.variables || []).length > 0 && <Badge variant="secondary">{template.variables.length} 变量</Badge>}
                          <span className="text-xs text-gray-500 dark:text-gray-400">{template.usage_count || 0} 次使用</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(event) => {
                            event.stopPropagation()
                            handlePreviewTemplate(template)
                          }}
                        >
                          <Eye className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(event) => {
                            event.stopPropagation()
                            handleQuickApply(template)
                          }}
                        >
                          <Wand2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {previewTemplate && (
          <div className="flex w-80 flex-col">
            <div className="border-b p-4">
              <div className="mb-2 flex items-center justify-between">
                <h4 className="font-semibold">{previewTemplate.template.title}</h4>
                <Button variant="ghost" size="sm" onClick={() => setPreviewTemplate(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">{previewTemplate.template.description}</p>
            </div>

            {(previewTemplate.template.variables || []).length > 0 && (
              <div className="border-b p-4">
                <h5 className="mb-3 text-sm font-medium">变量设置</h5>
                <div className="max-h-32 space-y-3 overflow-y-auto">
                  {previewTemplate.template.variables.map((variable) => (
                    <div key={variable.name}>
                      <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                        {variable.name}
                        {variable.required && <span className="ml-1 text-red-500 dark:text-red-400">*</span>}
                      </label>
                      <Input
                        value={previewVariables[variable.name] || ''}
                        onChange={(event) => handleUpdatePreviewVariable(variable.name, event.target.value)}
                        placeholder={variable.description}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex-1 p-4">
              <h5 className="mb-2 text-sm font-medium">预览效果</h5>
              <div className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded border bg-gray-50 p-3 text-sm dark:bg-gray-800/50">
                {previewTemplate.renderedContent}
              </div>
            </div>

            <div className="border-t p-4">
              <div className="flex gap-2">
                <Button size="sm" onClick={() => handleApplyTemplate(previewTemplate.template, previewVariables)} className="flex-1">
                  <Wand2 className="mr-1 h-3 w-3" />
                  应用模板
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    await navigator.clipboard.writeText(previewTemplate.renderedContent)
                    toast({ title: '已复制', description: '模板内容已复制到剪贴板', variant: 'success' })
                  }}
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
