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
  const [matrixView, setMatrixView] = useState<'list' | 'matrix'>('list')
  const [selectedSourceType, setSelectedSourceType] = useState<string>('REQUIREMENT')
  const [selectedTargetType, setSelectedTargetType] = useState<string>('DESIGN')

  useEffect(() => {
    loadTraceabilityData()
  }, [filters])

  const loadTraceabilityData = async () => {
    try {
      // TODO: 调用追溯矩阵API
      // const data = await traceabilityService.getTraceabilityMatrix(filters)
      // setTraceabilityData(data)
      
      // 模拟数据
      const mockData: TraceabilityItem[] = [
        {
          id: 1,
          source_id: 101,
          source_type: 'REQUIREMENT',
          source_code: 'REQ-2024-001',
          source_title: '用户登录功能',
          target_id: 201,
          target_type: 'DESIGN',
          target_code: 'DES-2024-001',
          target_title: '登录模块设计',
          trace_type: 'FORWARD',
          relationship: 'IMPLEMENTS',
          coverage_status: 'COVERED',
          confidence_level: 'HIGH',
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-01-15T10:00:00Z'
        },
        {
          id: 2,
          source_id: 101,
          source_type: 'REQUIREMENT',
          source_code: 'REQ-2024-001',
          source_title: '用户登录功能',
          target_id: 301,
          target_type: 'TEST_CASE',
          target_code: 'TC-2024-001',
          target_title: '登录功能测试',
          trace_type: 'FORWARD',
          relationship: 'TESTS',
          coverage_status: 'COVERED',
          confidence_level: 'HIGH',
          created_at: '2024-01-15T11:00:00Z',
          updated_at: '2024-01-15T11:00:00Z'
        },
        {
          id: 3,
          source_id: 102,
          source_type: 'REQUIREMENT',
          source_code: 'REQ-2024-002',
          source_title: '数据导出功能',
          target_id: 202,
          target_type: 'DESIGN',
          target_code: 'DES-2024-002',
          target_title: '导出模块设计',
          trace_type: 'FORWARD',
          relationship: 'IMPLEMENTS',
          coverage_status: 'PARTIAL',
          confidence_level: 'MEDIUM',
          created_at: '2024-01-16T09:00:00Z',
          updated_at: '2024-01-16T09:00:00Z'
        },
        {
          id: 4,
          source_id: 103,
          source_type: 'REQUIREMENT',
          source_code: 'REQ-2024-003',
          source_title: '权限管理功能',
          target_id: 0,
          target_type: 'DESIGN',
          target_code: '',
          target_title: '',
          trace_type: 'FORWARD',
          relationship: 'IMPLEMENTS',
          coverage_status: 'UNCOVERED',
          confidence_level: 'LOW',
          created_at: '2024-01-17T14:00:00Z',
          updated_at: '2024-01-17T14:00:00Z'
        }
      ]
      setTraceabilityData(mockData)
    } catch (error) {
      console.error('加载追溯矩阵数据失败:', error)
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

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <Loading />
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
                {/* 矩阵表头 */}
                <div className="grid grid-cols-6 gap-2 mb-4">
                  <div className="font-medium text-sm text-gray-700 dark:text-gray-300">
                    {getTypeText(selectedSourceType)} \ {getTypeText(selectedTargetType)}
                  </div>
                  <div className="text-center text-sm font-medium text-gray-700 dark:text-gray-300">DES-001</div>
                  <div className="text-center text-sm font-medium text-gray-700 dark:text-gray-300">DES-002</div>
                  <div className="text-center text-sm font-medium text-gray-700 dark:text-gray-300">DES-003</div>
                  <div className="text-center text-sm font-medium text-gray-700 dark:text-gray-300">DES-004</div>
                  <div className="text-center text-sm font-medium text-gray-700 dark:text-gray-300">DES-005</div>
                </div>

                {/* 矩阵内容 */}
                <div className="space-y-2">
                  {['REQ-001', 'REQ-002', 'REQ-003', 'REQ-004'].map((reqCode, rowIndex) => (
                    <div key={reqCode} className="grid grid-cols-6 gap-2 items-center">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{reqCode}</div>
                      {[0, 1, 2, 3, 4].map((colIndex) => {
                        const hasTrace = (rowIndex + colIndex) % 3 !== 2
                        const coverage = hasTrace ? 
                          (rowIndex + colIndex) % 3 === 0 ? 'COVERED' : 'PARTIAL' : 
                          'UNCOVERED'
                        
                        return (
                          <div key={colIndex} className="text-center">
                            {hasTrace ? (
                              <Tooltip content={`${reqCode} → DES-00${colIndex + 1}`}>
                                <div className={`w-6 h-6 rounded-full mx-auto cursor-pointer ${
                                  coverage === 'COVERED' ? 'bg-green-500' :
                                  coverage === 'PARTIAL' ? 'bg-yellow-500' : 'bg-red-500'
                                }`} />
                              </Tooltip>
                            ) : (
                              <div className="w-6 h-6 rounded-full mx-auto bg-gray-200 dark:bg-gray-600" />
                            )}
                          </div>
                        )
                      })}
                    </div>
                  ))}
                </div>

                {/* 图例 */}
                <div className="mt-6 flex justify-center space-x-6">
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 rounded-full bg-green-500" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">完全覆盖</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 rounded-full bg-yellow-500" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">部分覆盖</span>
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