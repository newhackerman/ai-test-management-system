// @ts-nocheck
import { useState } from 'react'
import { GripVertical, Maximize2, MoreVertical, RefreshCw, Settings, X } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu'
import { Widget } from '@/hooks/dashboard/useDashboard'
import { DataUpdater, useDataUpdater } from '../Realtime/DataUpdater'
import WidgetContent from '../Widgets/WidgetContent'

interface GridItemProps {
  widget: Widget
  editMode: boolean
  onRemove: (widgetId: string) => void
  onUpdate: (widgetId: string, updates: Partial<Widget>) => void
  realtimeData?: any
  dragHandleProps?: any
}

const GridItem: React.FC<GridItemProps> = ({
  widget,
  editMode,
  onRemove,
  onUpdate,
  realtimeData,
  dragHandleProps,
}) => {
  const [isLoading, setIsLoading] = useState(false)
  const [showConfig, setShowConfig] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    data: widgetRealtimeData,
    isUpdating,
    updateCount,
    lastUpdateTime,
    hasNewData,
  } = useDataUpdater(widget.id)

  const handleRefresh = async () => {
    setIsLoading(true)
    setError(null)

    try {
      await new Promise((resolve) => setTimeout(resolve, 500))
      onUpdate(widget.id, {
        data: {
          ...widget.data,
          lastUpdated: new Date().toISOString(),
        },
      })
    } catch (err: any) {
      setError(err?.message || '刷新失败')
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusColor = () => {
    if (error) return 'bg-red-500'
    if (isLoading || isUpdating) return 'bg-yellow-500'
    if (widgetRealtimeData || realtimeData) return 'bg-green-500'
    return 'bg-gray-400'
  }

  const getStatusText = () => {
    if (error) return '错误'
    if (isLoading) return '加载中'
    if (isUpdating) return '更新中'
    if (widgetRealtimeData || realtimeData) return '实时'
    return '静态'
  }

  return (
    <DataUpdater
      widgetId={widget.id}
      animationType="pulse"
      animationDuration={1000}
      showUpdateIndicator
      onDataUpdate={(data) => console.log(`Widget ${widget.id} updated:`, data)}
    >
      <Card className={`flex h-full flex-col ${editMode ? 'ring-2 ring-blue-200' : ''} ${isUpdating ? 'ring-2 ring-green-300' : ''}`}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex min-w-0 items-center gap-2">
            {editMode && (
              <div {...dragHandleProps} className="cursor-move rounded p-1 hover:bg-gray-100" title="拖拽移动">
                <GripVertical className="h-4 w-4 text-gray-400" />
              </div>
            )}

            <CardTitle className="truncate text-sm font-medium">{widget.title}</CardTitle>

            <Badge variant="outline" className={`border-none text-xs text-white ${getStatusColor()}`}>
              {getStatusText()}
            </Badge>

            {hasNewData && updateCount > 0 && (
              <Badge variant="outline" className="bg-blue-100 text-xs text-blue-600">
                {updateCount} 次更新
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-1">
            {!editMode && (
              <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={isLoading} className="h-6 w-6 p-0" title="刷新数据">
                <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
              </Button>
            )}

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0" title="更多选项">
                  <MoreVertical className="h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem onClick={() => setShowConfig(true)}>
                  <Settings className="mr-2 h-4 w-4" />
                  配置组件
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleRefresh} disabled={isLoading}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  刷新数据
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Maximize2 className="mr-2 h-4 w-4" />
                  全屏查看
                </DropdownMenuItem>
                {editMode && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => onRemove(widget.id)} className="text-red-600 focus:text-red-600">
                      <X className="mr-2 h-4 w-4" />
                      删除组件
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-hidden p-3">
          {error ? (
            <div className="flex h-full items-center justify-center text-center">
              <div>
                <div className="mb-2 text-red-500">
                  <X className="mx-auto h-8 w-8" />
                </div>
                <p className="mb-2 text-sm text-red-600">{error}</p>
                <Button size="sm" variant="outline" onClick={handleRefresh}>
                  重试
                </Button>
              </div>
            </div>
          ) : (
            <WidgetContent
              widget={widget}
              realtimeData={widgetRealtimeData || realtimeData}
              isLoading={isLoading || isUpdating}
              lastUpdateTime={lastUpdateTime}
            />
          )}
        </CardContent>

        {showConfig && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
            <div className="w-full max-w-md rounded-lg bg-white p-6">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold">配置组件</h3>
                <Button variant="ghost" size="sm" onClick={() => setShowConfig(false)} className="h-6 w-6 p-0">
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium">组件标题</label>
                  <input
                    type="text"
                    value={widget.title}
                    onChange={(event) => onUpdate(widget.id, { title: event.target.value })}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium">刷新间隔（秒）</label>
                  <select
                    value={widget.config.refreshInterval || 30}
                    onChange={(event) =>
                      onUpdate(widget.id, {
                        config: { ...widget.config, refreshInterval: Number(event.target.value) },
                      })
                    }
                    className="w-full rounded-md border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={10}>10 秒</option>
                    <option value={30}>30 秒</option>
                    <option value={60}>1 分钟</option>
                    <option value={300}>5 分钟</option>
                    <option value={600}>10 分钟</option>
                  </select>
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowConfig(false)}>
                  取消
                </Button>
                <Button onClick={() => setShowConfig(false)}>保存</Button>
              </div>
            </div>
          </div>
        )}
      </Card>
    </DataUpdater>
  )
}

export default GridItem
