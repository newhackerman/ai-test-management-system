import React, { useMemo, useState } from 'react'
import { Activity, BarChart3, List, Plus, Search, TrendingUp } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { useWidgets } from '@/hooks/dashboard/useWidgets'
import type { WidgetDefinition } from '@/services/dashboard/widgetService'

interface WidgetLibraryProps {
  isOpen: boolean
  onClose: () => void
  onAddWidget: (widgetType: string, config: Record<string, unknown>) => void
  roleType?: string
  currentUser?: {
    id: number
    role: string
    permissions: string[]
  }
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Activity,
  BarChart3,
  List,
  TrendingUp,
}

const categoryNames: Record<string, string> = {
  all: '全部',
  statistics: '统计',
  charts: '图表',
  lists: '列表',
  status: '状态',
  other: '其他',
}

const WidgetLibrary: React.FC<WidgetLibraryProps> = ({
  isOpen,
  onClose,
  onAddWidget,
  roleType = 'USER',
  currentUser,
}) => {
  const [keyword, setKeyword] = useState('')
  const [category, setCategory] = useState('all')
  const [previewWidget, setPreviewWidget] = useState<WidgetDefinition | null>(null)
  const { widgets, loading } = useWidgets(roleType, currentUser?.id)

  const categories = useMemo(() => {
    const set = new Set(['all', ...widgets.map((widget) => widget.category)])
    return Array.from(set)
  }, [widgets])

  const filteredWidgets = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    return widgets.filter((widget) => {
      const matchesCategory = category === 'all' || widget.category === category
      const matchesKeyword =
        !normalized ||
        widget.name.toLowerCase().includes(normalized) ||
        widget.description.toLowerCase().includes(normalized) ||
        widget.tags?.some((tag) => tag.toLowerCase().includes(normalized))
      return matchesCategory && matchesKeyword && widget.availability?.available !== false
    })
  }, [category, keyword, widgets])

  const addWidget = (widget: WidgetDefinition) => {
    onAddWidget(widget.type, widget.defaultConfig)
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>组件库</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索组件" className="pl-9" />
          </div>

          <Tabs value={category} onValueChange={setCategory}>
            <TabsList className="flex flex-wrap">
              {categories.map((item) => (
                <TabsTrigger key={item} value={item}>
                  {categoryNames[item] || item}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value={category} className="mt-4">
              {loading ? (
                <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">组件加载中...</div>
              ) : filteredWidgets.length === 0 ? (
                <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">暂无可用组件</div>
              ) : (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {filteredWidgets.map((widget) => {
                    const Icon = iconMap[widget.icon] || BarChart3
                    return (
                      <Card key={widget.id} className="flex flex-col">
                        <CardHeader className="space-y-3">
                          <div className="flex items-center justify-between">
                            <Icon className="h-6 w-6 text-primary" />
                            <Badge variant="outline">{categoryNames[widget.category] || widget.category}</Badge>
                          </div>
                          <CardTitle className="text-lg">{widget.name}</CardTitle>
                          <p className="text-sm text-muted-foreground">{widget.description}</p>
                        </CardHeader>
                        <CardContent className="mt-auto flex items-center justify-between">
                          <Button type="button" variant="outline" onClick={() => setPreviewWidget(widget)}>
                            预览
                          </Button>
                          <Button type="button" onClick={() => addWidget(widget)}>
                            <Plus className="mr-2 h-4 w-4" />
                            添加
                          </Button>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>

        {previewWidget && (
          <div className="mt-4 rounded-md border p-4">
            <div className="mb-2 font-medium">{previewWidget.name}</div>
            <div className="grid grid-cols-3 gap-3 text-center text-sm">
              <div className="rounded-md bg-muted p-3"><div className="text-xl font-semibold">128</div><div className="text-muted-foreground">总数</div></div>
              <div className="rounded-md bg-muted p-3"><div className="text-xl font-semibold">96</div><div className="text-muted-foreground">完成</div></div>
              <div className="rounded-md bg-muted p-3"><div className="text-xl font-semibold">+12%</div><div className="text-muted-foreground">趋势</div></div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default WidgetLibrary
