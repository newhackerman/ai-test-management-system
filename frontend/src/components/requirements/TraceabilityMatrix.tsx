import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Table } from '@/components/ui/Table'
import { Loading } from '@/components/ui/Loading'
import { Tooltip } from '@/components/ui/Tooltip'
import {
  GitBranch,
  ArrowRight,
  ArrowLeft,
  ArrowUpDown,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Eye,
  Edit,
  Plus
} from 'lucide-react'
import { traceabilityService, type MatrixType } from '@/services/traceabilityService'

interface MatrixViewData {
  requirements: Array<Record<string, any>>
  targets: Array<Record<string, any>>
  matrixData: Record<string, Record<string, boolean>>
  generatedAt: string
}

/** 目标类型到后端矩阵类型的映射。后端只有三种矩阵；选 REQUIREMENT 作目标时退到需求→用例矩阵。 */
function matrixTypeForTarget(targetType: string): MatrixType {
  if (targetType === 'TEST_CASE' || targetType === 'REQUIREMENT') return 'requirement_to_test'
  if (targetType === 'IMPLEMENTATION') return 'requirement_to_task'
  return 'requirement_to_design'
}

interface TraceabilityItem {
  id: number
  source_id: number
  source_type: 'REQUIREMENT' | 'DESIGN' | 'TEST_CASE' | 'IMPLEMENTATION'
  source_code: string
  source_title: string
  target_id: number
  target_type: 'REQUIREMENT' | 'DESIGN' | 'TEST_CASE' | 'IMPLEMENTATION'
  target_code: string
  target_title: string
  trace_type: 'FORWARD' | 'BACKWARD' | 'BIDIRECTIONAL'
  relationship: 'DERIVES_FROM' | 'IMPLEMENTS' | 'TESTS' | 'DEPENDS_ON' | 'SATISFIES'
  coverage_status: 'COVERED' | 'PARTIAL' | 'UNCOVERED'
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW'
  created_at: string
  updated_at: string
}

interface TraceabilityMatrixProps {
  filters?: any
  loading: boolean
  onRefresh: () => void
}

export function TraceabilityMatrix({
  filters,
  loading,
  onRefresh
}: TraceabilityMatrixProps) {
  const [traceabilityData, setTraceabilityData] = useState<TraceabilityItem[]>([])
  const [matrixViewData, setMatrixViewData] = useState<MatrixViewData | null>(null)
  const [matrixView, setMatrixView] = useState<'list' | 'matrix'>('list')
  const [selectedSourceType, setSelectedSourceType] = useState<string>('REQUIREMENT')
  const [selectedTargetType, setSelectedTargetType] = useState<string>('TEST_CASE')
  const [fetching, setFetching] = useState(false)
  const [fetchError, setFetchError] = useState('')

  useEffect(() => {
    loadTraceabilityData()
  }, [filters, selectedTargetType])

  const loadTraceabilityData = async () => {
    const projectId = Number((filters as any)?.project_id)
    if (!projectId) {
      setTraceabilityData([])
      setMatrixViewData(null)
      return
    }
    setFetching(true)
    setFetchError('')
    try {
      const matrixType = matrixTypeForTarget(selectedTargetType)
      const data = await traceabilityService.getTraceabilityMatrix(projectId, matrixType)
      const targetType = (selectedTargetType === 'REQUIREMENT' ? 'TEST_CASE' : selectedTargetType) as TraceabilityItem['target_type']
      const relationship = matrixType === 'requirement_to_test' ? 'TESTS' : 'IMPLEMENTS'
      const reqById = new Map<number, Record<string, any>>(data.requirements.map((r: any) => [r.id, r]))
      const targetById = new Map<number, Record<string, any>>(data.targets.map((t: any) => [t.id, t]))
      const items: TraceabilityItem[] = []
      const coveredReqIds = new Set<number>()
      let idSeq = 1
      Object.entries(data.matrix_data || {}).forEach(([reqId, targets]) => {
        const req = reqById.get(Number(reqId))
        if (!req) return
        Object.entries(targets as Record<string, boolean>).forEach(([targetId, linked]) => {
          if (!linked) return
          const target = targetById.get(Number(targetId))
          if (!target) return
          coveredReqIds.add(req.id)
          items.push({
            id: idSeq++,
            source_id: req.id,
            source_type: 'REQUIREMENT',
            source_code: req.requirement_code || `REQ-${req.id}`,
            source_title: req.title || '',
            target_id: target.id,
            target_type: targetType,
            target_code: target.code || `${targetType}-${target.id}`,
            target_title: target.title || '',
            trace_type: 'FORWARD',
            relationship,
            coverage_status: 'COVERED',
            confidence_level: 'HIGH',
            created_at: data.generated_at,
            updated_at: data.generated_at,
          })
        })
      })
      // 没有任何追溯链接的需求单独列一行未覆盖
      data.requirements.forEach((req: any) => {
        if (!coveredReqIds.has(req.id)) {
          items.push({
            id: idSeq++,
            source_id: req.id,
            source_type: 'REQUIREMENT',
            source_code: req.requirement_code || `REQ-${req.id}`,
            source_title: req.title || '',
            target_id: 0,
            target_type: targetType,
            target_code: '',
            target_title: '',
            trace_type: 'FORWARD',
            relationship: 'IMPLEMENTS',
            coverage_status: 'UNCOVERED',
            confidence_level: 'LOW',
            created_at: data.generated_at,
            updated_at: data.generated_at,
          })
        }
      })
      setTraceabilityData(items)
      setMatrixViewData({
        requirements: data.requirements,
        targets: data.targets,
        matrixData: data.matrix_data || {},
        generatedAt: data.generated_at,
      })
    } catch (error) {
      console.error('加载追溯矩阵数据失败:', error)
      setFetchError('加载追溯矩阵失败，请确认已选择项目后重试')
      setTraceabilityData([])
      setMatrixViewData(null)
    } finally {
      setFetching(false)
    }
  }

  const getTraceTypeIcon = (type: string) => {
    switch (type) {
      case 'FORWARD':
        return <ArrowRight className="w-4 h-4" />
      case 'BACKWARD':
        return <ArrowLeft className="w-4 h-4" />
      case 'BIDIRECTIONAL':
        return <ArrowUpDown className="w-4 h-4" />
      default:
        return <GitBranch className="w-4 h-4" />
    }
  }

  const getCoverageStatusBadge = (status: string) => {
    const statusConfig = {
      COVERED: { color: 'bg-green-100 text-green-800', icon: CheckCircle, text: '已覆盖' },
      PARTIAL: { color: 'bg-yellow-100 text-yellow-800', icon: AlertTriangle, text: '部分覆盖' },
      UNCOVERED: { color: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30', icon: XCircle, text: '未覆盖' }
    }

    const config = statusConfig[status as keyof typeof statusConfig]
    const Icon = config.icon

    return (
      <Badge className={config.color}>
        <Icon className="w-3 h-3 mr-1" />
        {config.text}
      </Badge>
    )
  }

  const getConfidenceBadge = (level: string) => {
    const levelConfig = {
      HIGH: { color: 'bg-green-100 text-green-800', text: '高' },
      MEDIUM: { color: 'bg-yellow-100 text-yellow-800', text: '中' },
      LOW: { color: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30', text: '低' }
    }

    const config = levelConfig[level as keyof typeof levelConfig]

    return (
      <Badge variant="outline" className={config.color}>
        {config.text}
      </Badge>
    )
  }

  const getRelationshipText = (relationship: string) => {
    const relationshipMap = {
      DERIVES_FROM: '派生自',
      IMPLEMENTS: '实现',
      TESTS: '测试',
      DEPENDS_ON: '依赖于',
      SATISFIES: '满足'
    }
    return relationshipMap[relationship as keyof typeof relationshipMap] || relationship
  }

  const getTypeText = (type: string) => {
    const typeMap = {
      REQUIREMENT: '需求',
      DESIGN: '设计',
      TEST_CASE: '测试用例',
      IMPLEMENTATION: '实现'
    }
    return typeMap[type as keyof typeof typeMap] || type
  }

  if (loading || fetching) {
    return (
      <div className="flex justify-center items-center py-8">
        <Loading />
      </div>
    )
  }

  if (fetchError) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 dark:text-red-400">{fetchError}</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={loadTraceabilityData}>
          重试
        </Button>
      </div>
    )
  }

  if (!(filters as any)?.project_id) {
    return (
      <div className="text-center py-8">
        <GitBranch className="w-12 h-12 text-gray-400 mx-auto mb-4 dark:text-gray-500" />
        <h3 className="text-lg font-medium text-gray-900 mb-2 dark:text-gray-100">请先选择项目</h3>
        <p className="text-gray-500 dark:text-gray-400">追溯矩阵按项目生成，请在上方筛选器中选择一个项目</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 视图切换和操作 */}
      <div className="flex justify-between items-center">
        <div className="flex space-x-2">
          <Button
            variant={matrixView === 'list' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setMatrixView('list')}
          >
            列表视图
          </Button>
          <Button
            variant={matrixView === 'matrix' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setMatrixView('matrix')}
          >
            矩阵视图
          </Button>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" size="sm">
            <Plus className="w-4 h-4 mr-2" />
            添加追溯关系
          </Button>
          <Button variant="outline" size="sm" onClick={onRefresh}>
            刷新
          </Button>
        </div>
      </div>

      {/* 列表视图 */}
      {matrixView === 'list' && (
        <Card>
          <CardHeader>
            <CardTitle>追溯关系列表</CardTitle>
          </CardHeader>
          <CardContent>
            {traceabilityData.length === 0 ? (
              <div className="text-center py-8">
                <GitBranch className="w-12 h-12 text-gray-400 mx-auto mb-4 dark:text-gray-500" />
                <h3 className="text-lg font-medium text-gray-900 mb-2 dark:text-gray-100">暂无追溯关系</h3>
                <p className="text-gray-500 dark:text-gray-400">当前筛选条件下没有找到追溯关系</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <thead>
                    <tr>
                      <th className="text-left">源项目</th>
                      <th className="text-center">关系</th>
                      <th className="text-left">目标项目</th>
                      <th className="text-center">覆盖状态</th>
                      <th className="text-center">置信度</th>
                      <th className="text-right">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {traceabilityData.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50 dark:bg-gray-800/50 dark:hover:bg-gray-800">
                        <td>
                          <div>
                            <div className="font-medium text-gray-900 dark:text-gray-100">
                              {item.source_code}
                            </div>
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                              {item.source_title}
                            </div>
                            <div className="text-xs text-gray-500 mt-1 dark:text-gray-400">
                              {getTypeText(item.source_type)}
                            </div>
                          </div>
                        </td>
                        <td className="text-center">
                          <div className="flex flex-col items-center space-y-1">
                            <Tooltip content={`${getRelationshipText(item.relationship)} (${item.trace_type})`}>
                              <div className="flex items-center space-x-1">
                                {getTraceTypeIcon(item.trace_type)}
                                <span className="text-xs text-gray-600 dark:text-gray-400">
                                  {getRelationshipText(item.relationship)}
                                </span>
                              </div>
                            </Tooltip>
                          </div>
                        </td>
                        <td>
                          {item.coverage_status === 'UNCOVERED' ? (
                            <div className="text-gray-400 dark:text-gray-500">
                              <div className="text-sm">未建立追溯关系</div>
                              <div className="text-xs">需要创建目标项目</div>
                            </div>
                          ) : (
                            <div>
                              <div className="font-medium text-gray-900 dark:text-gray-100">
                                {item.target_code}
                              </div>
                              <div className="text-sm text-gray-600 dark:text-gray-400">
                                {item.target_title}
                              </div>
                              <div className="text-xs text-gray-500 mt-1 dark:text-gray-400">
                                {getTypeText(item.target_type)}
                              </div>
                            </div>
                          )}
                        </td>
                        <td className="text-center">
                          {getCoverageStatusBadge(item.coverage_status)}
                        </td>
                        <td className="text-center">
                          {getConfidenceBadge(item.confidence_level)}
                        </td>
                        <td>
                          <div className="flex justify-end space-x-2">
                            <Button variant="ghost" size="sm">
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Edit className="w-4 h-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 矩阵视图 */}
      {matrixView === 'matrix' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>追溯矩阵</span>
              <div className="flex space-x-2">
                <select
                  value={selectedSourceType}
                  onChange={(e) => setSelectedSourceType(e.target.value)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="REQUIREMENT">需求</option>
                  <option value="DESIGN">设计</option>
                  <option value="TEST_CASE">测试用例</option>
                  <option value="IMPLEMENTATION">实现</option>
                </select>
                <span className="text-sm text-gray-500 self-center dark:text-gray-400">→</span>
                <select
                  value={selectedTargetType}
                  onChange={(e) => setSelectedTargetType(e.target.value)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="REQUIREMENT">需求</option>
                  <option value="DESIGN">设计</option>
                  <option value="TEST_CASE">测试用例</option>
                  <option value="IMPLEMENTATION">实现</option>
                </select>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <div className="min-w-full">
                {/* 矩阵表头：行=需求，列=目标（均取自后端矩阵接口，最多各展示 10 个） */}
                {!matrixViewData || matrixViewData.requirements.length === 0 || matrixViewData.targets.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    {matrixViewData ? '当前矩阵没有目标列（该类型下暂无目标对象或追溯链接）' : '请先选择项目以加载追溯矩阵'}
                  </div>
                ) : (
                  <div>
                    <div
                      className="grid gap-2 mb-4 items-center"
                      style={{ gridTemplateColumns: `minmax(120px, 1.5fr) repeat(${Math.min(matrixViewData.targets.length, 10)}, 1fr)` }}
                    >
                      <div className="font-medium text-sm text-gray-700 dark:text-gray-300">
                        {getTypeText(selectedSourceType)} \ {getTypeText(selectedTargetType)}
                      </div>
                      {matrixViewData.targets.slice(0, 10).map((target: any) => (
                        <div key={target.id} className="text-center text-sm font-medium text-gray-700 dark:text-gray-300" title={target.title || ''}>
                          {target.code || `${selectedTargetType}-${target.id}`}
                        </div>
                      ))}
                    </div>

                    {/* 矩阵内容 */}
                    <div className="space-y-2">
                      {matrixViewData.requirements.slice(0, 10).map((req: any) => {
                        const reqCode = req.requirement_code || `REQ-${req.id}`
                        return (
                          <div
                            key={req.id}
                            className="grid gap-2 items-center"
                            style={{ gridTemplateColumns: `minmax(120px, 1.5fr) repeat(${Math.min(matrixViewData.targets.length, 10)}, 1fr)` }}
                          >
                            <div className="text-sm font-medium text-gray-900 dark:text-gray-100" title={req.title || ''}>{reqCode}</div>
                            {matrixViewData.targets.slice(0, 10).map((target: any) => {
                              const linked = Boolean(matrixViewData.matrixData[String(req.id)]?.[String(target.id)])
                              const targetCode = target.code || `${selectedTargetType}-${target.id}`
                              return (
                                <div key={target.id} className="text-center">
                                  {linked ? (
                                    <Tooltip content={`${reqCode} → ${targetCode}`}>
                                      <div className="w-6 h-6 rounded-full mx-auto cursor-pointer bg-green-500" />
                                    </Tooltip>
                                  ) : (
                                    <div className="w-6 h-6 rounded-full mx-auto bg-gray-200 dark:bg-gray-600" />
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* 图例 */}
                <div className="mt-6 flex justify-center space-x-6">
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 rounded-full bg-green-500" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">完全覆盖</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 rounded-full bg-red-500" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">未覆盖</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 rounded-full bg-gray-200 dark:bg-gray-600" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">无关系</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 统计信息 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {traceabilityData.filter(item => item.coverage_status === 'COVERED').length}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">完全覆盖</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {traceabilityData.filter(item => item.coverage_status === 'PARTIAL').length}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">部分覆盖</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {traceabilityData.filter(item => item.coverage_status === 'UNCOVERED').length}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">未覆盖</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
              {Math.round((traceabilityData.filter(item => item.coverage_status === 'COVERED').length / traceabilityData.length) * 100) || 0}%
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">覆盖率</div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default TraceabilityMatrix