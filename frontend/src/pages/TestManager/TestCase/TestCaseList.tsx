import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, Filter, Download, Upload, Copy, Trash2, Wand2, Bot } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Input } from '../../../components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { Checkbox } from '../../../components/ui/Checkbox'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../../components/ui/DropdownMenu'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/Select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../../components/ui/Dialog'
import { 
  useTestCases, 
  useTestCaseManagement, 
  useDeleteTestCase, 
  useDuplicateTestCase,
  useBatchDeleteTestCases,
  useExportTestCases,
  useImportTestCases,
  useGenerateTestCases
} from '../../../hooks/testmanager/useTestCase'
import { TestCaseStatus, TestCaseType, Priority, Complexity, AutomationLevel } from '../../../types/testmanager'
import { formatDate } from '../../../utils/date'
import requirementService from '../../../services/requirementService'
import type { Requirement } from '../../../types/requirement'

const TestCaseList: React.FC = () => {
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [showGenerateDialog, setShowGenerateDialog] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [generateRequirementId, setGenerateRequirementId] = useState('')
  const [requirements, setRequirements] = useState<Requirement[]>([])

  const {
    selectedCases,
    filters,
    searchTerm,
    handleSelectCase,
    handleSelectAllCases,
    handleClearSelection,
    handleUpdateFilters,
    handleSearch,
  } = useTestCaseManagement()

  const { data: testCasesData, isLoading, error } = useTestCases(filters)
  const deleteTestCase = useDeleteTestCase()
  const duplicateTestCase = useDuplicateTestCase()
  const batchDeleteTestCases = useBatchDeleteTestCases()
  const exportTestCases = useExportTestCases()
  const importTestCases = useImportTestCases()
  const generateTestCases = useGenerateTestCases()

  const testCases = testCasesData?.data || []
  const totalCount = testCasesData?.total || 0
  const requirementMap = useMemo(() => {
    const map = new Map<number, Requirement>()
    requirements.forEach((requirement) => map.set(Number(requirement.id), requirement))
    return map
  }, [requirements])

  useEffect(() => {
    let cancelled = false
    requirementService.getRequirements({ page: 1, size: 100, sort_by: 'updated_at', sort_order: 'desc' })
      .then((response) => {
        if (!cancelled) setRequirements(response.data || [])
      })
      .catch(() => {
        if (!cancelled) setRequirements([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleDelete = (id: number) => {
    if (window.confirm('确定要删除这个测试用例吗？')) {
      deleteTestCase.mutate(id)
    }
  }

  const handleBatchDelete = () => {
    if (window.confirm(`确定要删除选中的 ${selectedCases.length} 个测试用例吗？`)) {
      batchDeleteTestCases.mutate(selectedCases)
      handleClearSelection()
    }
  }

  const handleExport = (format: string) => {
    exportTestCases.mutate({ filters, format })
  }

  const handleDuplicate = (id: number, title: string) => {
    const newTitle = window.prompt('请输入复制后的测试用例标题', `${title} - 副本`)
    if (newTitle) duplicateTestCase.mutate({ id, newTitle })
  }

  const handleImport = () => {
    if (importFile) {
      importTestCases.mutate({ file: importFile })
      setImportFile(null)
      setShowImportDialog(false)
    }
  }

  const handleGenerate = () => {
    const requirementId = Number(generateRequirementId)
    if (!Number.isFinite(requirementId) || requirementId <= 0) {
      window.alert('请输入有效的需求ID')
      return
    }
    generateTestCases.mutate({
      requirement_id: requirementId,
      case_type: TestCaseType.FUNCTIONAL,
      priority: Priority.MEDIUM,
    })
    setShowGenerateDialog(false)
    setGenerateRequirementId('')
  }

  const getStatusBadge = (status: TestCaseStatus) => {
    const statusConfig = {
      [TestCaseStatus.DRAFT]: { label: '草稿', variant: 'secondary' as const },
      [TestCaseStatus.APPROVED]: { label: '已批准', variant: 'default' as const },
      [TestCaseStatus.ACTIVE]: { label: '活跃', variant: 'default' as const },
      [TestCaseStatus.DEPRECATED]: { label: '已废弃', variant: 'secondary' as const },
      [TestCaseStatus.ARCHIVED]: { label: '已归档', variant: 'outline' as const },
    }
    
    const config = statusConfig[status]
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const getPriorityBadge = (priority: Priority) => {
    const priorityConfig = {
      [Priority.CRITICAL]: { label: '紧急', variant: 'destructive' as const },
      [Priority.HIGH]: { label: '高', variant: 'destructive' as const },
      [Priority.MEDIUM]: { label: '中', variant: 'default' as const },
      [Priority.LOW]: { label: '低', variant: 'secondary' as const },
    }
    
    const config = priorityConfig[priority]
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  const getTypeLabel = (type: TestCaseType) => {
    const typeLabels = {
      [TestCaseType.FUNCTIONAL]: '功能',
      [TestCaseType.NON_FUNCTIONAL]: '非功能',
      [TestCaseType.INTEGRATION]: '集成',
      [TestCaseType.SYSTEM]: '系统',
      [TestCaseType.ACCEPTANCE]: '验收',
      [TestCaseType.REGRESSION]: '回归',
      [TestCaseType.SMOKE]: '冒烟',
      [TestCaseType.PERFORMANCE]: '性能',
      [TestCaseType.SECURITY]: '安全',
      [TestCaseType.USABILITY]: '易用性',
    }
    return typeLabels[type] || type
  }

  const getAutomationLabel = (level: AutomationLevel) => {
    const labels = {
      [AutomationLevel.MANUAL]: '手动',
      [AutomationLevel.SEMI_AUTO]: '半自动',
      [AutomationLevel.FULL_AUTO]: '全自动',
    }
    return labels[level] || level
  }

  const getRequirementLabel = (requirementId?: number) => {
    if (!requirementId) return '未关联'
    const requirement = requirementMap.get(Number(requirementId))
    if (!requirement) return `需求 #${requirementId}`
    return requirement.requirement_code
      ? `${requirement.requirement_code} - ${requirement.title}`
      : requirement.title
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
          <h1 className="text-2xl font-bold">测试用例管理</h1>
          <p className="text-gray-600">设计、维护和管理测试用例库</p>
        </div>
        <div className="flex space-x-2">
          <Dialog open={showGenerateDialog} onOpenChange={setShowGenerateDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Bot className="w-4 h-4 mr-2" />
                AI生成
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>AI生成测试用例</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">需求ID</label>
                  <Input
                    value={generateRequirementId}
                    onChange={(event) => setGenerateRequirementId(event.target.value)}
                    placeholder="输入已有需求ID后生成用例"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowGenerateDialog(false)}>
                    取消
                  </Button>
                  <Button onClick={handleGenerate} disabled={generateTestCases.isPending}>
                    生成
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
          
          <Link to="/test-manager/test-cases/create">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              创建用例
            </Button>
          </Link>
        </div>
      </div>      {/* 
Filters and Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="搜索测试用例..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Select
                value={filters.status || 'all'}
                onValueChange={(value) => handleUpdateFilters({ status: value === 'all' ? undefined : value as TestCaseStatus })}
              >
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value={TestCaseStatus.DRAFT}>草稿</SelectItem>
                  <SelectItem value={TestCaseStatus.APPROVED}>已批准</SelectItem>
                  <SelectItem value={TestCaseStatus.ACTIVE}>活跃</SelectItem>
                  <SelectItem value={TestCaseStatus.DEPRECATED}>已废弃</SelectItem>
                  <SelectItem value={TestCaseStatus.ARCHIVED}>已归档</SelectItem>
                </SelectContent>
              </Select>
              
              <Select
                value={filters.case_type || 'all'}
                onValueChange={(value) => handleUpdateFilters({ case_type: value === 'all' ? undefined : value as TestCaseType })}
              >
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  <SelectItem value={TestCaseType.FUNCTIONAL}>功能</SelectItem>
                  <SelectItem value={TestCaseType.NON_FUNCTIONAL}>非功能</SelectItem>
                  <SelectItem value={TestCaseType.INTEGRATION}>集成</SelectItem>
                  <SelectItem value={TestCaseType.SYSTEM}>系统</SelectItem>
                  <SelectItem value={TestCaseType.ACCEPTANCE}>验收</SelectItem>
                  <SelectItem value={TestCaseType.REGRESSION}>回归</SelectItem>
                  <SelectItem value={TestCaseType.SMOKE}>冒烟</SelectItem>
                  <SelectItem value={TestCaseType.PERFORMANCE}>性能</SelectItem>
                  <SelectItem value={TestCaseType.SECURITY}>安全</SelectItem>
                  <SelectItem value={TestCaseType.USABILITY}>易用性</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={filters.priority || 'all'}
                onValueChange={(value) => handleUpdateFilters({ priority: value === 'all' ? undefined : value as Priority })}
              >
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="优先级" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部优先级</SelectItem>
                  <SelectItem value={Priority.CRITICAL}>紧急</SelectItem>
                  <SelectItem value={Priority.HIGH}>高</SelectItem>
                  <SelectItem value={Priority.MEDIUM}>中</SelectItem>
                  <SelectItem value={Priority.LOW}>低</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={filters.requirement_id ? String(filters.requirement_id) : 'all'}
                onValueChange={(value) => handleUpdateFilters({ requirement_id: value === 'all' ? undefined : Number(value) })}
              >
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="关联需求" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部需求</SelectItem>
                  {requirements.map((requirement) => (
                    <SelectItem key={requirement.id} value={String(requirement.id)}>
                      {requirement.requirement_code || `REQ-${requirement.id}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Batch Actions */}
      {selectedCases.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">
                已选择 {selectedCases.length} 个测试用例
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleClearSelection}>
                  取消选择
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      批量操作
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => handleExport('excel')}>
                      <Download className="w-4 h-4 mr-2" />
                      导出选中
                    </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => selectedCases.forEach((id) => {
                          const source = testCases.find((item) => item.id === id)
                          if (source) duplicateTestCase.mutate({ id, newTitle: `${source.case_title} - 副本` })
                        })}>
                          <Copy className="w-4 h-4 mr-2" />
                          批量复制
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={handleBatchDelete} className="text-red-600">
                      <Trash2 className="w-4 h-4 mr-2" />
                      批量删除
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex justify-between items-center">
            <div className="flex gap-2">
              <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Upload className="w-4 h-4 mr-2" />
                    导入用例
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>导入测试用例</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">选择文件</label>
                      <input
                        type="file"
                        accept=".xlsx,.xls,.csv"
                        onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                      />
                    </div>
                    <div className="flex justify-end space-x-2">
                      <Button variant="outline" onClick={() => setShowImportDialog(false)}>
                        取消
                      </Button>
                      <Button onClick={handleImport} disabled={!importFile}>
                        导入
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
              
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-2" />
                    导出
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleExport('excel')}>
                    导出为 Excel
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExport('csv')}>
                    导出为 CSV
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExport('pdf')}>
                    导出为 PDF
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            
            <div className="text-sm text-gray-600">
              共 {totalCount} 个测试用例
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Test Cases Table */}
      <Card>
        <CardHeader>
          <CardTitle>测试用例列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={selectedCases.length === testCases.length && testCases.length > 0}
                    onCheckedChange={() => handleSelectAllCases(testCases.map(c => c.id))}
                  />
                </TableHead>
                <TableHead>用例标题</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>优先级</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>关联需求</TableHead>
                <TableHead>自动化</TableHead>
                <TableHead>负责人</TableHead>
                <TableHead>更新时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {testCases.map((testCase) => (
                <TableRow key={testCase.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedCases.includes(testCase.id)}
                      onCheckedChange={() => handleSelectCase(testCase.id)}
                    />
                  </TableCell>
                  <TableCell>
                    <div>
                      <Link 
                        to={`/test-manager/test-cases/${testCase.id}`}
                        className="font-medium text-blue-600 hover:text-blue-800"
                      >
                        {testCase.case_title}
                      </Link>
                      <div className="text-sm text-gray-500">{testCase.case_code}</div>
                      {testCase.module && (
                        <div className="text-xs text-gray-400">{testCase.module}</div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{getTypeLabel(testCase.case_type)}</Badge>
                  </TableCell>
                  <TableCell>{getPriorityBadge(testCase.priority)}</TableCell>
                  <TableCell>{getStatusBadge(testCase.status)}</TableCell>
                  <TableCell>
                    {testCase.requirement_id ? (
                      <div className="max-w-[220px] truncate text-sm text-gray-700" title={getRequirementLabel(testCase.requirement_id)}>
                        {getRequirementLabel(testCase.requirement_id)}
                      </div>
                    ) : (
                      <span className="text-sm text-gray-400">未关联</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">
                      {getAutomationLabel(testCase.automation_level)}
                    </Badge>
                  </TableCell>
                  <TableCell>负责人</TableCell>
                  <TableCell>{formatDate(testCase.updated_at)}</TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          操作
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem asChild>
                          <Link to={`/test-manager/test-cases/${testCase.id}`}>
                            查看详情
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link to={`/test-manager/test-cases/${testCase.id}/edit`}>
                            编辑
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDuplicate(testCase.id, testCase.case_title)}>
                          <Copy className="w-4 h-4 mr-2" />
                          复制
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Wand2 className="w-4 h-4 mr-2" />
                          生成自动化脚本
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          className="text-red-600"
                          onClick={() => handleDelete(testCase.id)}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          删除
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          {testCases.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              暂无测试用例数据
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default TestCaseList
