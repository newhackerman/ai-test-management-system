import React from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, Download, Copy, Trash2, Play, Pause, CheckCircle } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Input } from '../../../components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { Checkbox } from '../../../components/ui/Checkbox'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../../components/ui/DropdownMenu'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { Progress } from '../../../components/ui/Progress'
import { useTestPlans, useTestPlanManagement, useDeleteTestPlan, useUpdateTestPlanStatus, useDuplicateTestPlan, useExportTestPlan } from '../../../hooks/testmanager/useTestPlan'
import { TestPlanStatus, TestType } from '../../../types/testmanager'
import { formatDate } from '../../../utils/date'

const TestPlanList: React.FC = () => {
  const {
    selectedPlans,
    filters,
    searchTerm,
    handleSelectPlan,
    handleSelectAllPlans,
    handleClearSelection,
    handleUpdateFilters,
    handleSearch,
  } = useTestPlanManagement()

  const { data: testPlansData, isLoading, error } = useTestPlans(filters)
  const deleteTestPlan = useDeleteTestPlan()
  const updateTestPlanStatus = useUpdateTestPlanStatus()
  const duplicateTestPlan = useDuplicateTestPlan()
  const exportTestPlan = useExportTestPlan()

  const testPlans = testPlansData?.data || []
  const totalCount = testPlansData?.total || 0

  const handleStatusChange = (id: number, status: TestPlanStatus) => {
    updateTestPlanStatus.mutate({ id, status })
  }

  const handleDelete = (id: number) => {
    if (window.confirm('确定要删除这个测试计划吗？')) {
      deleteTestPlan.mutate(id)
    }
  }

  const handleBatchDelete = () => {
    if (window.confirm(`确定要删除选中的 ${selectedPlans.length} 个测试计划吗？`)) {
      selectedPlans.forEach((id) => deleteTestPlan.mutate(id))
      handleClearSelection()
    }
  }

  const handleDuplicate = (id: number, name: string) => {
    const newName = window.prompt('请输入复制后的测试计划名称', `${name} - 副本`)
    if (newName) duplicateTestPlan.mutate({ id, newName })
  }

  const handleExport = (id: number, format: 'csv' | 'txt') => {
    exportTestPlan.mutate({ id, format })
  }

  const getStatusBadge = (status: TestPlanStatus) => {
    const statusConfig = {
      [TestPlanStatus.DRAFT]: { label: '草稿', variant: 'secondary' as const },
      [TestPlanStatus.APPROVED]: { label: '已批准', variant: 'default' as const },
      [TestPlanStatus.IN_PROGRESS]: { label: '进行中', variant: 'default' as const },
      [TestPlanStatus.PAUSED]: { label: '暂停', variant: 'secondary' as const },
      [TestPlanStatus.COMPLETED]: { label: '已完成', variant: 'default' as const },
      [TestPlanStatus.CANCELLED]: { label: '已取消', variant: 'destructive' as const },
    }
    
    const config = statusConfig[status]
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const getTypeLabel = (type: TestType) => {
    const typeLabels = {
      [TestType.FUNCTIONAL]: '功能测试',
      [TestType.PERFORMANCE]: '性能测试',
      [TestType.SECURITY]: '安全测试',
      [TestType.INTEGRATION]: '集成测试',
      [TestType.REGRESSION]: '回归测试',
      [TestType.ACCEPTANCE]: '验收测试',
    }
    return typeLabels[type] || type
  }

  if (isLoading) {
    return <div className="flex justify-center items-center h-64">加载中...</div>
  }

  if (error) {
    return <div className="text-red-500 text-center">加载失败: {error.message}</div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">测试计划管理</h1>
          <p className="text-gray-600">管理和监控测试计划的执行进度</p>
        </div>
        <Link to="/test-manager/test-plans/create">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            创建测试计划
          </Button>
        </Link>
      </div>  
    {/* Filters and Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="搜索测试计划..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Select
                value={filters.status || 'all'}
                onValueChange={(value) => handleUpdateFilters({ status: value === 'all' ? undefined : value as TestPlanStatus })}
              >
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value={TestPlanStatus.DRAFT}>草稿</SelectItem>
                  <SelectItem value={TestPlanStatus.APPROVED}>已批准</SelectItem>
                  <SelectItem value={TestPlanStatus.IN_PROGRESS}>进行中</SelectItem>
                  <SelectItem value={TestPlanStatus.PAUSED}>暂停</SelectItem>
                  <SelectItem value={TestPlanStatus.COMPLETED}>已完成</SelectItem>
                  <SelectItem value={TestPlanStatus.CANCELLED}>已取消</SelectItem>
                </SelectContent>
              </Select>
              
              <Select
                value={filters.test_type || 'all'}
                onValueChange={(value) => handleUpdateFilters({ test_type: value === 'all' ? undefined : value as TestType })}
              >
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  <SelectItem value={TestType.FUNCTIONAL}>功能测试</SelectItem>
                  <SelectItem value={TestType.PERFORMANCE}>性能测试</SelectItem>
                  <SelectItem value={TestType.SECURITY}>安全测试</SelectItem>
                  <SelectItem value={TestType.INTEGRATION}>集成测试</SelectItem>
                  <SelectItem value={TestType.REGRESSION}>回归测试</SelectItem>
                  <SelectItem value={TestType.ACCEPTANCE}>验收测试</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Batch Actions */}
      {selectedPlans.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">
                已选择 {selectedPlans.length} 个测试计划
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleClearSelection}>
                  取消选择
                </Button>
                <Button variant="destructive" size="sm" onClick={handleBatchDelete}>
                  <Trash2 className="w-4 h-4 mr-2" />
                  批量删除
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Test Plans Table */}
      <Card>
        <CardHeader>
          <CardTitle>测试计划列表 ({totalCount})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={selectedPlans.length === testPlans.length && testPlans.length > 0}
                    onCheckedChange={() => handleSelectAllPlans(testPlans.map((plan: any) => plan.id))}
                  />
                </TableHead>
                <TableHead>计划名称</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>进度</TableHead>
                <TableHead>开始日期</TableHead>
                <TableHead>结束日期</TableHead>
                <TableHead>测试经理</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {testPlans.map((plan: any) => {
                const executionRate = plan.total_cases > 0 ? (plan.executed_cases / plan.total_cases) * 100 : 0
                const passRate = plan.executed_cases > 0 ? (plan.passed_cases / plan.executed_cases) * 100 : 0
                
                return (
                  <TableRow key={plan.id}>
                    <TableCell>
                      <Checkbox
                        checked={selectedPlans.includes(plan.id)}
                        onCheckedChange={() => handleSelectPlan(plan.id)}
                      />
                    </TableCell>
                    <TableCell>
                      <div>
                        <Link 
                          to={`/test-manager/test-plans/${plan.id}`}
                          className="font-medium text-blue-600 hover:text-blue-800"
                        >
                          {plan.plan_name}
                        </Link>
                        <div className="text-sm text-gray-500">{plan.plan_code}</div>
                      </div>
                    </TableCell>
                    <TableCell>{getTypeLabel(plan.test_type)}</TableCell>
                    <TableCell>{getStatusBadge(plan.status)}</TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span>执行率</span>
                          <span>{executionRate.toFixed(1)}%</span>
                        </div>
                        <Progress value={executionRate} className="h-2" />
                        <div className="flex justify-between text-xs text-gray-500">
                          <span>通过率: {passRate.toFixed(1)}%</span>
                          <span>{plan.executed_cases}/{plan.total_cases}</span>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{plan.planned_start_date ? formatDate(plan.planned_start_date) : '-'}</TableCell>
                    <TableCell>{plan.planned_end_date ? formatDate(plan.planned_end_date) : '-'}</TableCell>
                    <TableCell>测试经理</TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            操作
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem>
                            <Link to={`/test-manager/test-plans/${plan.id}`}>
                              查看详情
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem asChild>
                            <Link to={`/test-manager/test-plans/${plan.id}/edit`}>
                              编辑
                            </Link>
                          </DropdownMenuItem>
                          {plan.status === TestPlanStatus.DRAFT && (
                            <DropdownMenuItem onClick={() => handleStatusChange(plan.id, TestPlanStatus.APPROVED)}>
                              <CheckCircle className="w-4 h-4 mr-2" />
                              批准
                            </DropdownMenuItem>
                          )}
                          {plan.status === TestPlanStatus.APPROVED && (
                            <DropdownMenuItem onClick={() => handleStatusChange(plan.id, TestPlanStatus.IN_PROGRESS)}>
                              <Play className="w-4 h-4 mr-2" />
                              开始执行
                            </DropdownMenuItem>
                          )}
                          {plan.status === TestPlanStatus.IN_PROGRESS && (
                            <DropdownMenuItem onClick={() => handleStatusChange(plan.id, TestPlanStatus.PAUSED)}>
                              <Pause className="w-4 h-4 mr-2" />
                              暂停
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem onClick={() => handleDuplicate(plan.id, plan.plan_name)}>
                            <Copy className="w-4 h-4 mr-2" />
                            复制
                          </DropdownMenuItem>
                          <DropdownMenuItem disabled={exportTestPlan.isPending} onClick={() => handleExport(plan.id, 'csv')}>
                            <Download className="w-4 h-4 mr-2" />
                            导出 CSV
                          </DropdownMenuItem>
                          <DropdownMenuItem disabled={exportTestPlan.isPending} onClick={() => handleExport(plan.id, 'txt')}>
                            <Download className="w-4 h-4 mr-2" />
                            导出 TXT
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            className="text-red-600"
                            onClick={() => handleDelete(plan.id)}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            删除
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          
          {testPlans.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              暂无测试计划数据
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default TestPlanList
