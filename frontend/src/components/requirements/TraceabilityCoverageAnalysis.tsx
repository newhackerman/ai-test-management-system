import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Table } from '@/components/ui/Table'
import { Loading } from '@/components/ui/Loading'
import { 
  BarChart3, 
  PieChart, 
  TrendingUp, 
  TrendingDown,
  Target,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Eye,
  Download,
  RefreshCw
} from 'lucide-react'

interface CoverageData {
  requirement_id: number
  requirement_code: string
  requirement_title: string
  requirement_type: string
  priority: string
  forward_coverage: number
  backward_coverage: number
  bidirectional_coverage: number
  design_coverage: number
  test_coverage: number
  implementation_coverage: number
  overall_coverage: number
  coverage_status: 'EXCELLENT' | 'GOOD' | 'FAIR' | 'POOR'
  gaps: Array<{
    type: string
    description: string
    severity: 'HIGH' | 'MEDIUM' | 'LOW'
  }>
}

interface CoverageStatistics {
  total_requirements: number
  traced_requirements: number
  untraced_requirements: number
  coverage_percentage: number
  forward_traceability: number
  backward_traceability: number
  bidirectional_traceability: number
  by_type: Record<string, {
    total: number
    covered: number
    percentage: number
  }>
  by_priority: Record<string, {
    total: number
    covered: number
    percentage: number
  }>
  trends: {
    coverage_trend: number
    improvement_rate: number
    period: string
  }
}

interface TraceabilityCoverageAnalysisProps {
  statistics: any
  filters?: any
  loading: boolean
  onRefresh: () => void
}

export function TraceabilityCoverageAnalysis({
  statistics,
  filters,
  loading,
  onRefresh
}: TraceabilityCoverageAnalysisProps) {
  const [coverageData, setCoverageData] = useState<CoverageData[]>([])
  const [detailedStats, setDetailedStats] = useState<CoverageStatistics | null>(null)
  const [selectedView, setSelectedView] = useState<'overview' | 'detailed' | 'trends'>('overview')
  const [sortBy, setSortBy] = useState<'coverage' | 'priority' | 'type'>('coverage')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    loadCoverageData()
    loadDetailedStatistics()
  }, [filters])

  const loadCoverageData = async () => {
    try {
      // TODO: 调用覆盖率分析API
      // const data = await traceabilityService.getCoverageAnalysis(filters)
      // setCoverageData(data)
      
      // 模拟数据
      const mockData: CoverageData[] = [
        {
          requirement_id: 101,
          requirement_code: 'REQ-2024-001',
          requirement_title: '用户登录功能',
          requirement_type: 'FUNCTIONAL',
          priority: 'HIGH',
          forward_coverage: 95,
          backward_coverage: 90,
          bidirectional_coverage: 85,
          design_coverage: 100,
          test_coverage: 90,
          implementation_coverage: 95,
          overall_coverage: 92,
          coverage_status: 'EXCELLENT',
          gaps: []
        },
        {
          requirement_id: 102,
          requirement_code: 'REQ-2024-002',
          requirement_title: '数据导出功能',
          requirement_type: 'FUNCTIONAL',
          priority: 'MEDIUM',
          forward_coverage: 70,
          backward_coverage: 60,
          bidirectional_coverage: 55,
          design_coverage: 80,
          test_coverage: 50,
          implementation_coverage: 70,
          overall_coverage: 65,
          coverage_status: 'FAIR',
          gaps: [
            {
              type: 'TEST_COVERAGE',
              description: '缺少集成测试用例',
              severity: 'MEDIUM'
            }
          ]
        },
        {
          requirement_id: 103,
          requirement_code: 'REQ-2024-003',
          requirement_title: '权限管理功能',
          requirement_type: 'FUNCTIONAL',
          priority: 'HIGH',
          forward_coverage: 30,
          backward_coverage: 20,
          bidirectional_coverage: 15,
          design_coverage: 40,
          test_coverage: 0,
          implementation_coverage: 30,
          overall_coverage: 25,
          coverage_status: 'POOR',
          gaps: [
            {
              type: 'DESIGN_COVERAGE',
              description: '缺少详细设计文档',
              severity: 'HIGH'
            },
            {
              type: 'TEST_COVERAGE',
              description: '未创建测试用例',
              severity: 'HIGH'
            }
          ]
        }
      ]
      setCoverageData(mockData)
    } catch (error) {
      console.error('加载覆盖率数据失败:', error)
    }
  }

  const loadDetailedStatistics = async () => {
    try {
      // TODO: 调用详细统计API
      // const stats = await traceabilityService.getDetailedStatistics(filters)
      // setDetailedStats(stats)
      
      // 模拟统计数据
      const mockStats: CoverageStatistics = {
        total_requirements: 150,
        traced_requirements: 120,
        untraced_requirements: 30,
        coverage_percentage: 80,
        forward_traceability: 85,
        backward_traceability: 75,
        bidirectional_traceability: 70,
        by_type: {
          FUNCTIONAL: { total: 100, covered: 85, percentage: 85 },
          NON_FUNCTIONAL: { total: 30, covered: 20, percentage: 67 },
          CONSTRAINT: { total: 15, covered: 10, percentage: 67 },
          INTERFACE: { total: 5, covered: 5, percentage: 100 }
        },
        by_priority: {
          CRITICAL: { total: 20, covered: 18, percentage: 90 },
          HIGH: { total: 50, covered: 45, percentage: 90 },
          MEDIUM: { total: 60, covered: 45, percentage: 75 },
          LOW: { total: 20, covered: 12, percentage: 60 }
        },
        trends: {
          coverage_trend: 5.2,
          improvement_rate: 8.5,
          period: '本月'
        }
      }
      setDetailedStats(mockStats)
    } catch (error) {
      console.error('加载详细统计失败:', error)
    }
  }

  const getCoverageStatusBadge = (status: string) => {
    const statusConfig = {
      EXCELLENT: { color: 'bg-green-100 text-green-800', icon: CheckCircle, text: '优秀' },
      GOOD: { color: 'bg-blue-100 text-blue-800 dark:text-blue-300 dark:bg-blue-900/30', icon: CheckCircle, text: '良好' },
      FAIR: { color: 'bg-yellow-100 text-yellow-800', icon: AlertTriangle, text: '一般' },
      POOR: { color: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30', icon: XCircle, text: '较差' }
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

  const getCoverageColor = (percentage: number) => {
    if (percentage >= 90) return 'text-green-600 dark:text-green-400'
    if (percentage >= 70) return 'text-blue-600 dark:text-blue-400'
    if (percentage >= 50) return 'text-yellow-600'
    return 'text-red-600 dark:text-red-400'
  }

  const sortedCoverageData = [...coverageData].sort((a, b) => {
    let aValue, bValue
    
    switch (sortBy) {
      case 'coverage':
        aValue = a.overall_coverage
        bValue = b.overall_coverage
        break
      case 'priority':
        const priorityOrder = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 }
        aValue = priorityOrder[a.priority as keyof typeof priorityOrder]
        bValue = priorityOrder[b.priority as keyof typeof priorityOrder]
        break
      case 'type':
        aValue = a.requirement_type
        bValue = b.requirement_type
        break
      default:
        return 0
    }

    if (sortOrder === 'asc') {
      return aValue > bValue ? 1 : -1
    } else {
      return aValue < bValue ? 1 : -1
    }
  })

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <Loading />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 视图切换 */}
      <div className="flex justify-between items-center">
        <div className="flex space-x-2">
          <Button
            variant={selectedView === 'overview' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedView('overview')}
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            概览
          </Button>
          <Button
            variant={selectedView === 'detailed' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedView('detailed')}
          >
            <Target className="w-4 h-4 mr-2" />
            详细分析
          </Button>
          <Button
            variant={selectedView === 'trends' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedView('trends')}
          >
            <TrendingUp className="w-4 h-4 mr-2" />
            趋势分析
          </Button>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="w-4 h-4 mr-2" />
            刷新
          </Button>
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            导出报告
          </Button>
        </div>
      </div>

      {/* 概览视图 */}
      {selectedView === 'overview' && (
        <div className="space-y-6">
          {/* 总体覆盖率 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">前向追溯覆盖率</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <div className={`text-3xl font-bold ${getCoverageColor(statistics.forward_traceability)}`}>
                    {statistics.forward_traceability}%
                  </div>
                  <Progress value={statistics.forward_traceability} className="mt-2" />
                  <p className="text-sm text-gray-600 mt-2 dark:text-gray-400">需求 → 设计 → 实现</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">后向追溯覆盖率</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <div className={`text-3xl font-bold ${getCoverageColor(statistics.backward_traceability)}`}>
                    {statistics.backward_traceability}%
                  </div>
                  <Progress value={statistics.backward_traceability} className="mt-2" />
                  <p className="text-sm text-gray-600 mt-2 dark:text-gray-400">实现 → 设计 → 需求</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">双向追溯覆盖率</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <div className={`text-3xl font-bold ${getCoverageColor(statistics.bidirectional_traceability)}`}>
                    {statistics.bidirectional_traceability}%
                  </div>
                  <Progress value={statistics.bidirectional_traceability} className="mt-2" />
                  <p className="text-sm text-gray-600 mt-2 dark:text-gray-400">完整的追溯链</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 按类型和优先级分析 */}
          {detailedStats && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>按需求类型覆盖率</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(detailedStats.by_type).map(([type, data]) => (
                      <div key={type} className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm font-medium">
                            {type === 'FUNCTIONAL' ? '功能需求' :
                             type === 'NON_FUNCTIONAL' ? '非功能需求' :
                             type === 'CONSTRAINT' ? '约束需求' : '接口需求'}
                          </span>
                          <span className={`text-sm font-bold ${getCoverageColor(data.percentage)}`}>
                            {data.percentage}%
                          </span>
                        </div>
                        <Progress value={data.percentage} />
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {data.covered} / {data.total} 个需求已覆盖
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>按优先级覆盖率</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(detailedStats.by_priority).map(([priority, data]) => (
                      <div key={priority} className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm font-medium">
                            {priority === 'CRITICAL' ? '关键' :
                             priority === 'HIGH' ? '高' :
                             priority === 'MEDIUM' ? '中' : '低'}优先级
                          </span>
                          <span className={`text-sm font-bold ${getCoverageColor(data.percentage)}`}>
                            {data.percentage}%
                          </span>
                        </div>
                        <Progress value={data.percentage} />
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {data.covered} / {data.total} 个需求已覆盖
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* 详细分析视图 */}
      {selectedView === 'detailed' && (
        <div className="space-y-6">
          {/* 排序控制 */}
          <div className="flex space-x-2">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'coverage' | 'priority' | 'type')}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="coverage">按覆盖率排序</option>
              <option value="priority">按优先级排序</option>
              <option value="type">按类型排序</option>
            </select>
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="desc">降序</option>
              <option value="asc">升序</option>
            </select>
          </div>

          {/* 详细覆盖率表格 */}
          <Card>
            <CardHeader>
              <CardTitle>需求覆盖率详细分析</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <thead>
                    <tr>
                      <th className="text-left">需求</th>
                      <th className="text-center">类型</th>
                      <th className="text-center">优先级</th>
                      <th className="text-center">设计覆盖</th>
                      <th className="text-center">测试覆盖</th>
                      <th className="text-center">实现覆盖</th>
                      <th className="text-center">总体覆盖</th>
                      <th className="text-center">状态</th>
                      <th className="text-right">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedCoverageData.map((item) => (
                      <tr key={item.requirement_id} className="hover:bg-gray-50 dark:bg-gray-800/50 dark:hover:bg-gray-800">
                        <td>
                          <div>
                            <div className="font-medium text-gray-900 dark:text-gray-100">
                              {item.requirement_code}
                            </div>
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                              {item.requirement_title}
                            </div>
                          </div>
                        </td>
                        <td className="text-center">
                          <Badge variant="outline">
                            {item.requirement_type === 'FUNCTIONAL' ? '功能' :
                             item.requirement_type === 'NON_FUNCTIONAL' ? '非功能' :
                             item.requirement_type === 'CONSTRAINT' ? '约束' : '接口'}
                          </Badge>
                        </td>
                        <td className="text-center">
                          <Badge variant={
                            item.priority === 'CRITICAL' ? 'destructive' :
                            item.priority === 'HIGH' ? 'default' : 'secondary'
                          }>
                            {item.priority === 'CRITICAL' ? '关键' :
                             item.priority === 'HIGH' ? '高' :
                             item.priority === 'MEDIUM' ? '中' : '低'}
                          </Badge>
                        </td>
                        <td className="text-center">
                          <span className={getCoverageColor(item.design_coverage)}>
                            {item.design_coverage}%
                          </span>
                        </td>
                        <td className="text-center">
                          <span className={getCoverageColor(item.test_coverage)}>
                            {item.test_coverage}%
                          </span>
                        </td>
                        <td className="text-center">
                          <span className={getCoverageColor(item.implementation_coverage)}>
                            {item.implementation_coverage}%
                          </span>
                        </td>
                        <td className="text-center">
                          <div className="flex items-center justify-center space-x-2">
                            <span className={`font-bold ${getCoverageColor(item.overall_coverage)}`}>
                              {item.overall_coverage}%
                            </span>
                            <div className="w-16">
                              <Progress value={item.overall_coverage} />
                            </div>
                          </div>
                        </td>
                        <td className="text-center">
                          {getCoverageStatusBadge(item.coverage_status)}
                        </td>
                        <td>
                          <div className="flex justify-end space-x-2">
                            <Button variant="ghost" size="sm">
                              <Eye className="w-4 h-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 趋势分析视图 */}
      {selectedView === 'trends' && detailedStats && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>覆盖率趋势</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="flex items-center justify-center mb-2">
                    {detailedStats.trends.coverage_trend > 0 ? (
                      <TrendingUp className="w-6 h-6 text-green-600 dark:text-green-400" />
                    ) : (
                      <TrendingDown className="w-6 h-6 text-red-600 dark:text-red-400" />
                    )}
                  </div>
                  <div className={`text-2xl font-bold ${
                    detailedStats.trends.coverage_trend > 0 ? 'text-green-600' : 'text-red-600 dark:text-red-400'
                  }`}>
                    {detailedStats.trends.coverage_trend > 0 ? '+' : ''}{detailedStats.trends.coverage_trend}%
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">{detailedStats.trends.period}覆盖率变化</div>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center mb-2">
                    <Target className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {detailedStats.trends.improvement_rate}%
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">改进速度</div>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center mb-2">
                    <CheckCircle className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                    {Math.round((detailedStats.traced_requirements / detailedStats.total_requirements) * 100)}%
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">当前覆盖率</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 改进建议 */}
          <Card>
            <CardHeader>
              <CardTitle>改进建议</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 rounded-lg dark:bg-blue-900/20">
                  <h4 className="font-medium text-blue-900 mb-2 dark:text-blue-100">优先改进项</h4>
                  <ul className="space-y-1 text-sm text-blue-800 dark:text-blue-300">
                    <li>• 完善高优先级需求的测试覆盖率</li>
                    <li>• 建立功能需求与实现代码的双向追溯</li>
                    <li>• 补充缺失的设计文档追溯关系</li>
                  </ul>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <h4 className="font-medium text-green-900 mb-2">最佳实践</h4>
                  <ul className="space-y-1 text-sm text-green-800">
                    <li>• 在需求变更时及时更新追溯关系</li>
                    <li>• 定期审查和验证追溯关系的准确性</li>
                    <li>• 使用自动化工具维护追溯矩阵</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

export default TraceabilityCoverageAnalysis