import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Edit, Copy, Play, Wand2, FileText, Clock, User } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../../components/ui/Tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import { useTestCase } from '../../../hooks/testmanager/useTestCase'
import { TestCaseStatus, TestCaseType, Priority, Complexity, AutomationLevel } from '../../../types/testmanager'
import { formatDate } from '../../../utils/date'
import requirementService from '../../../services/requirementService'
import type { Requirement } from '../../../types/requirement'

const TestCaseDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const caseId = parseInt(id!, 10)

  const { data: testCase, isLoading, error } = useTestCase(caseId)
  const [requirement, setRequirement] = useState<Requirement | null>(null)
  const [requirementError, setRequirementError] = useState('')

  useEffect(() => {
    if (!testCase?.requirement_id) {
      setRequirement(null)
      setRequirementError('')
      return
    }

    let cancelled = false
    requirementService.getRequirement(Number(testCase.requirement_id))
      .then((data) => {
        if (!cancelled) {
          setRequirement(data)
          setRequirementError('')
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setRequirement(null)
          setRequirementError(loadError?.message || '需求加载失败')
        }
      })

    return () => {
      cancelled = true
    }
  }, [testCase?.requirement_id])

  if (isLoading) {
    return <div className="flex justify-center items-center h-64">加载中...</div>
  }

  if (error || !testCase) {
    return <div className="text-red-500 text-center">加载失败</div>
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
      [TestCaseType.FUNCTIONAL]: '功能测试',
      [TestCaseType.NON_FUNCTIONAL]: '非功能测试',
      [TestCaseType.INTEGRATION]: '集成测试',
      [TestCaseType.SYSTEM]: '系统测试',
      [TestCaseType.ACCEPTANCE]: '验收测试',
      [TestCaseType.REGRESSION]: '回归测试',
      [TestCaseType.SMOKE]: '冒烟测试',
      [TestCaseType.PERFORMANCE]: '性能测试',
      [TestCaseType.SECURITY]: '安全测试',
      [TestCaseType.USABILITY]: '易用性测试',
    }
    return typeLabels[type] || type
  }

  const getComplexityLabel = (complexity: Complexity) => {
    const labels = {
      [Complexity.SIMPLE]: '简单',
      [Complexity.MEDIUM]: '中等',
      [Complexity.COMPLEX]: '复杂',
    }
    return labels[complexity] || complexity
  }

  const getAutomationLabel = (level: AutomationLevel) => {
    const labels = {
      [AutomationLevel.MANUAL]: '手动',
      [AutomationLevel.SEMI_AUTO]: '半自动',
      [AutomationLevel.FULL_AUTO]: '全自动',
    }
    return labels[level] || level
  }

  const requirementText = testCase.requirement_id
    ? requirement
      ? `${requirement.requirement_code || `REQ-${requirement.id}`} - ${requirement.title}`
      : requirementError || `需求 #${testCase.requirement_id}`
    : '未关联需求'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/test-manager/test-cases">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回列表
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{testCase.case_title}</h1>
            <p className="text-gray-600">{testCase.case_code}</p>
          </div>
          {getStatusBadge(testCase.status)}
        </div>
        <div className="flex space-x-2">
          <Button variant="outline">
            <Play className="w-4 h-4 mr-2" />
            执行测试
          </Button>
          <Button variant="outline">
            <Copy className="w-4 h-4 mr-2" />
            复制
          </Button>
          <Button variant="outline">
            <Wand2 className="w-4 h-4 mr-2" />
            生成脚本
          </Button>
          <Link to={`/test-manager/test-cases/${caseId}/edit`}>
            <Button>
              <Edit className="w-4 h-4 mr-2" />
              编辑
            </Button>
          </Link>
        </div>
      </div>      
{/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <FileText className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">测试类型</p>
                <p className="text-lg font-semibold">{getTypeLabel(testCase.case_type)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 bg-red-500 rounded-full" />
              <div>
                <p className="text-sm font-medium text-gray-600">优先级</p>
                <div className="mt-1 text-lg font-semibold">{getPriorityBadge(testCase.priority)}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Clock className="w-5 h-5 text-green-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">复杂度</p>
                <p className="text-lg font-semibold">{getComplexityLabel(testCase.complexity)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <Wand2 className="w-5 h-5 text-purple-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">自动化</p>
                <p className="text-lg font-semibold">{getAutomationLabel(testCase.automation_level)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Information */}
      <Tabs defaultValue="details" className="space-y-4">
        <TabsList>
          <TabsTrigger value="details">用例详情</TabsTrigger>
          <TabsTrigger value="steps">测试步骤</TabsTrigger>
          <TabsTrigger value="executions">执行记录</TabsTrigger>
          <TabsTrigger value="history">变更历史</TabsTrigger>
        </TabsList>

        <TabsContent value="details">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>基本信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-600">用例描述</label>
                  <p className="mt-1">{testCase.case_description || '暂无描述'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">功能模块</label>
                  <p className="mt-1">{testCase.module || '未分类'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">关联需求</label>
                  <p className="mt-1">{requirementText}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">前置条件</label>
                  <p className="mt-1">{testCase.preconditions || '无特殊前置条件'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">预期结果</label>
                  <p className="mt-1">{testCase.expected_result || '暂无定义'}</p>
                </div>
                {testCase.tags && testCase.tags.length > 0 && (
                  <div>
                    <label className="text-sm font-medium text-gray-600">标签</label>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {testCase.tags.map((tag, index) => (
                        <Badge key={index} variant="outline">{tag}</Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>管理信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <User className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">创建人</label>
                    <p>创建者</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <User className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">负责人</label>
                    <p>负责人</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">创建时间</label>
                    <p>{formatDate(testCase.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">更新时间</label>
                    <p>{formatDate(testCase.updated_at)}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <FileText className="w-4 h-4 text-gray-500" />
                  <div>
                    <label className="text-sm font-medium text-gray-600">版本</label>
                    <p>v{testCase.version}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="steps">
          <Card>
            <CardHeader>
              <CardTitle>测试步骤</CardTitle>
            </CardHeader>
            <CardContent>
              {testCase.test_steps && testCase.test_steps.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">步骤</TableHead>
                      <TableHead>操作</TableHead>
                      <TableHead>预期结果</TableHead>
                      <TableHead>测试数据</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {testCase.test_steps.map((step, index) => (
                      <TableRow key={index}>
                        <TableCell className="font-medium">{step.step_number}</TableCell>
                        <TableCell>{step.action}</TableCell>
                        <TableCell>{step.expected_result}</TableCell>
                        <TableCell>
                          {step.test_data ? (
                            <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                              {JSON.stringify(step.test_data)}
                            </code>
                          ) : (
                            '-'
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  暂无测试步骤
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="executions">
          <Card>
            <CardHeader>
              <CardTitle>执行记录</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                执行记录将在这里显示
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle>变更历史</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                变更历史将在这里显示
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default TestCaseDetail
