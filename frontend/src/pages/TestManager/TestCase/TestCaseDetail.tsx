// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Clock, Copy, Edit, FileText, Play, User, Wand2 } from 'lucide-react'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { Badge } from '../../../components/ui/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../../components/ui/Tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import {
  useDuplicateTestCase,
  useGenerateAutomationScript,
  useTestCase,
} from '../../../hooks/testmanager/useTestCase'
import { useExecutions } from '../../../hooks/testmanager/useExecution'
import { formatDate } from '../../../utils/date'
import requirementService from '../../../services/requirementService'
import { testPlanService } from '../../../services/testmanager/testPlanService'
import userService from '../../../services/user-service'
import type { Requirement } from '../../../types/requirement'
import type { TestPlan } from '../../../types/testmanager'
import type { User as UserType } from '../../../types'
import {
  AUTOMATION_LABELS,
  COMPLEXITY_LABELS,
  EXECUTION_STATUS_LABELS,
  PRIORITY_LABELS,
  STATUS_LABELS,
  TEST_CASE_TYPE_LABELS,
} from './testCaseLabels'

const statusVariant = {
  DRAFT: 'secondary',
  APPROVED: 'default',
  ACTIVE: 'default',
  DEPRECATED: 'secondary',
  ARCHIVED: 'outline',
} as const

const priorityVariant = {
  CRITICAL: 'destructive',
  HIGH: 'destructive',
  MEDIUM: 'default',
  LOW: 'secondary',
} as const

const executionVariant = {
  PASSED: 'default',
  FAILED: 'destructive',
  BLOCKED: 'secondary',
  IN_PROGRESS: 'default',
  SKIPPED: 'outline',
  NOT_EXECUTED: 'outline',
} as const

const TestCaseDetail: React.FC = () => {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const caseId = Number(id)
  const { data: testCase, isLoading, error } = useTestCase(caseId)
  const { data: executionsData, isLoading: executionsLoading } = useExecutions({ test_case_id: caseId, page: 1, size: 20 })
  const duplicateTestCase = useDuplicateTestCase()
  const generateAutomationScript = useGenerateAutomationScript()
  const [requirement, setRequirement] = useState<Requirement | null>(null)
  const [testPlan, setTestPlan] = useState<TestPlan | null>(null)
  const [users, setUsers] = useState<UserType[]>([])

  useEffect(() => {
    let cancelled = false
    userService.getUsers({ page: 1, size: 100, status: 'active' })
      .then((response) => {
        if (!cancelled) setUsers(response.users || [])
      })
      .catch(() => {
        if (!cancelled) setUsers([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!testCase?.requirement_id) {
      setRequirement(null)
      return
    }
    let cancelled = false
    requirementService.getRequirement(Number(testCase.requirement_id))
      .then((data) => {
        if (!cancelled) setRequirement(data)
      })
      .catch(() => {
        if (!cancelled) setRequirement(null)
      })
    return () => {
      cancelled = true
    }
  }, [testCase?.requirement_id])

  useEffect(() => {
    if (!testCase?.test_plan_id) {
      setTestPlan(null)
      return
    }
    let cancelled = false
    testPlanService.getTestPlan(Number(testCase.test_plan_id))
      .then((data) => {
        if (!cancelled) setTestPlan(data)
      })
      .catch(() => {
        if (!cancelled) setTestPlan(null)
      })
    return () => {
      cancelled = true
    }
  }, [testCase?.test_plan_id])

  const userMap = useMemo(() => new Map(users.map((user) => [Number(user.id), user])), [users])
  const getUserName = (userId?: number) => {
    if (!userId) return '未分配'
    const user = userMap.get(Number(userId))
    return user?.real_name || user?.nickname || user?.username || `用户 #${userId}`
  }

  const handleDuplicate = () => {
    if (!testCase) return
    const newTitle = window.prompt('请输入复制后的测试用例标题', `${testCase.case_title} - 副本`)
    if (!newTitle?.trim()) return
    duplicateTestCase.mutate(
      { id: testCase.id, newTitle: newTitle.trim() },
      { onSuccess: (data) => data?.id && navigate(`/test-manager/test-cases/${data.id}`) },
    )
  }

  const handleGenerateScript = () => {
    generateAutomationScript.mutate({
      testCaseId: caseId,
      config: { framework: 'PLAYWRIGHT', language: 'PYTHON', browser: 'CHROME' },
    })
  }

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center">加载中...</div>
  }

  if (error || !testCase) {
    return <div className="text-center text-red-500 dark:text-red-400">加载失败</div>
  }

  const executions = executionsData?.data || []
  const requirementText = testCase.requirement_id
    ? requirement
      ? `${requirement.requirement_code || `REQ-${requirement.id}`} - ${requirement.title}`
      : `需求 #${testCase.requirement_id}`
    : '未关联需求'
  const planText = testCase.test_plan_id
    ? testPlan
      ? `${testPlan.plan_code || `TP-${testPlan.id}`} - ${testPlan.plan_name}`
      : `测试计划 #${testCase.test_plan_id}`
    : '未关联测试计划'

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <Link to="/test-manager/test-cases">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回列表
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{testCase.case_title}</h1>
            <p className="text-gray-600 dark:text-gray-400">{testCase.case_code}</p>
          </div>
          <Badge variant={statusVariant[testCase.status] || 'secondary'}>{STATUS_LABELS[testCase.status] || testCase.status}</Badge>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to={`/test-manager/executions/manual/${caseId}`}>
            <Button variant="outline">
              <Play className="mr-2 h-4 w-4" />
              执行测试
            </Button>
          </Link>
          <Button variant="outline" onClick={handleDuplicate} disabled={duplicateTestCase.isPending}>
            <Copy className="mr-2 h-4 w-4" />
            复制
          </Button>
          <Button variant="outline" onClick={handleGenerateScript} disabled={generateAutomationScript.isPending}>
            <Wand2 className="mr-2 h-4 w-4" />
            生成脚本
          </Button>
          <Link to={`/test-manager/test-cases/${caseId}/edit`}>
            <Button>
              <Edit className="mr-2 h-4 w-4" />
              编辑
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <MetricCard icon={<FileText className="h-5 w-5 text-blue-500 dark:text-blue-400" />} label="测试类型" value={TEST_CASE_TYPE_LABELS[testCase.case_type] || testCase.case_type} />
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400">优先级</p>
            <div className="mt-2"><Badge variant={priorityVariant[testCase.priority] || 'secondary'}>{PRIORITY_LABELS[testCase.priority] || testCase.priority}</Badge></div>
          </CardContent>
        </Card>
        <MetricCard icon={<Clock className="h-5 w-5 text-green-500" />} label="复杂度" value={COMPLEXITY_LABELS[testCase.complexity] || testCase.complexity} />
        <MetricCard icon={<Wand2 className="h-5 w-5 text-purple-500" />} label="自动化" value={AUTOMATION_LABELS[testCase.automation_level] || testCase.automation_level} />
      </div>

      <Tabs defaultValue="details" className="space-y-4">
        <TabsList>
          <TabsTrigger value="details">用例详情</TabsTrigger>
          <TabsTrigger value="steps">测试步骤</TabsTrigger>
          <TabsTrigger value="executions">执行记录</TabsTrigger>
          <TabsTrigger value="history">变更信息</TabsTrigger>
        </TabsList>

        <TabsContent value="details">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>业务信息</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <Info label="用例描述" value={testCase.case_description || '暂无描述'} />
                <Info label="功能模块" value={testCase.module || '未分类'} />
                <Info label="关联测试计划" value={planText} />
                <Info label="关联需求" value={requirementText} />
                <Info label="前置条件" value={testCase.preconditions || '无特殊前置条件'} />
                <Info label="总体预期结果" value={testCase.expected_result || '暂无定义'} />
                {Array.isArray(testCase.tags) && testCase.tags.length > 0 && (
                  <div>
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-400">标签</label>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {testCase.tags.map((tag, index) => <Badge key={`${tag}-${index}`} variant="outline">{tag}</Badge>)}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>管理信息</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <IconInfo icon={<User className="h-4 w-4 text-gray-500 dark:text-gray-400" />} label="创建人" value={getUserName(testCase.creator_id)} />
                <IconInfo icon={<User className="h-4 w-4 text-gray-500 dark:text-gray-400" />} label="负责人" value={getUserName(testCase.assignee_id)} />
                <IconInfo icon={<Clock className="h-4 w-4 text-gray-500 dark:text-gray-400" />} label="创建时间" value={formatDate(testCase.created_at)} />
                <IconInfo icon={<Clock className="h-4 w-4 text-gray-500 dark:text-gray-400" />} label="更新时间" value={formatDate(testCase.updated_at)} />
                <IconInfo icon={<FileText className="h-4 w-4 text-gray-500 dark:text-gray-400" />} label="版本" value={`v${testCase.version || 1}`} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="steps">
          <Card>
            <CardHeader><CardTitle>测试步骤</CardTitle></CardHeader>
            <CardContent>
              {Array.isArray(testCase.test_steps) && testCase.test_steps.length > 0 ? (
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
                        <TableCell className="font-medium">{step.step_number || index + 1}</TableCell>
                        <TableCell className="whitespace-pre-wrap">{step.action}</TableCell>
                        <TableCell className="whitespace-pre-wrap">{step.expected_result}</TableCell>
                        <TableCell className="whitespace-pre-wrap text-sm text-gray-600 dark:text-gray-400">
                          {typeof step.test_data === 'string' ? step.test_data || '-' : JSON.stringify(step.test_data || '') || '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="py-8 text-center text-gray-500 dark:text-gray-400">暂无测试步骤</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="executions">
          <Card>
            <CardHeader><CardTitle>执行记录</CardTitle></CardHeader>
            <CardContent>
              {executionsLoading ? (
                <div className="py-8 text-center text-gray-500 dark:text-gray-400">执行记录加载中...</div>
              ) : executions.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>执行编号</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>执行人</TableHead>
                      <TableHead>环境</TableHead>
                      <TableHead>开始时间</TableHead>
                      <TableHead>完成时间</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {executions.map((execution) => (
                      <TableRow key={execution.id}>
                        <TableCell>{execution.execution_code || `EXEC-${execution.id}`}</TableCell>
                        <TableCell><Badge variant={executionVariant[execution.execution_status] || 'secondary'}>{EXECUTION_STATUS_LABELS[execution.execution_status] || execution.execution_status}</Badge></TableCell>
                        <TableCell>{getUserName(execution.executor_id)}</TableCell>
                        <TableCell>{execution.test_environment || '-'}</TableCell>
                        <TableCell>{execution.started_at ? formatDate(execution.started_at) : '-'}</TableCell>
                        <TableCell>{execution.completed_at ? formatDate(execution.completed_at) : '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="py-8 text-center text-gray-500 dark:text-gray-400">
                  暂无执行记录，可点击页面右上角“执行测试”开始一次手工执行。
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader><CardTitle>变更信息</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Info label="当前版本" value={`v${testCase.version || 1}`} />
              <Info label="当前状态" value={STATUS_LABELS[testCase.status] || testCase.status} />
              <Info label="创建时间" value={formatDate(testCase.created_at)} />
              <Info label="最近更新时间" value={formatDate(testCase.updated_at)} />
              <Info label="创建人" value={getUserName(testCase.creator_id)} />
              <Info label="负责人" value={getUserName(testCase.assignee_id)} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

const MetricCard = ({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</p>
          <p className="text-lg font-semibold">{value}</p>
        </div>
      </div>
    </CardContent>
  </Card>
)

const Info = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div>
    <label className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</label>
    <p className="mt-1 whitespace-pre-wrap">{value}</p>
  </div>
)

const IconInfo = ({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) => (
  <div className="flex items-center gap-2">
    {icon}
    <Info label={label} value={value} />
  </div>
)

export default TestCaseDetail
