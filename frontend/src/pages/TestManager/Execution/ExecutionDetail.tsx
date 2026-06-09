import React from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Bug, FileText, Pause, Play, Square } from 'lucide-react'
import { Badge } from '../../../components/ui/Badge'
import { Button } from '../../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card'
import { ScrollArea } from '../../../components/ui/ScrollArea'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../../components/ui/Table'
import {
  useCancelExecution,
  useExecution,
  usePauseExecution,
  useResumeExecution,
} from '../../../hooks/testmanager/useExecution'
import { useCreateDefect, useDefects } from '../../../hooks/testmanager/useDefect'
import { DefectSeverity, DefectType, ExecutionStatus, ExecutionType, Priority } from '../../../types/testmanager'
import { formatDate } from '../../../utils/date'

const statusLabels: Record<string, string> = {
  NOT_EXECUTED: '未执行',
  IN_PROGRESS: '执行中',
  PASSED: '通过',
  FAILED: '失败',
  BLOCKED: '暂停/阻塞',
  SKIPPED: '已取消',
}

const statusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  NOT_EXECUTED: 'secondary',
  IN_PROGRESS: 'default',
  PASSED: 'default',
  FAILED: 'destructive',
  BLOCKED: 'secondary',
  SKIPPED: 'outline',
}

const formatDuration = (seconds?: number) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}分钟`
  return `${Math.floor(minutes / 60)}小时${minutes % 60}分钟`
}

const formatFileSize = (size?: number) => {
  if (!size) return '-'
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))}KB`
  return `${(size / 1024 / 1024).toFixed(1)}MB`
}

const getStepText = (log: any, key: string) => {
  const value = log?.[key]
  if (value === undefined || value === null || value === '') return '-'
  return String(value)
}

const buildFailureSteps = (logs: any[]) => {
  const failedLogs = logs.filter((log: any) => log?.status === ExecutionStatus.FAILED)
  const source = failedLogs.length ? failedLogs : logs
  if (!source.length) return '查看执行结论和失败原因。'

  return source.map((log: any, index: number) => [
    `${index + 1}. 操作：${getStepText(log, 'action')}`,
    `   预期：${getStepText(log, 'expected_result')}`,
    `   实际：${getStepText(log, 'actual_result')}`,
  ].join('\n')).join('\n\n')
}

const inferDefectSeverity = (priority?: string) => {
  if (priority === Priority.CRITICAL) return DefectSeverity.CRITICAL
  if (priority === Priority.HIGH) return DefectSeverity.HIGH
  return DefectSeverity.MEDIUM
}

const ExecutionDetail: React.FC = () => {
  const { executionId } = useParams<{ executionId: string }>()
  const id = Number(executionId)
  const { data: execution, isLoading } = useExecution(id)
  const pauseExecution = usePauseExecution()
  const resumeExecution = useResumeExecution()
  const cancelExecution = useCancelExecution()
  const createDefect = useCreateDefect()
  const { data: linkedDefectsData } = useDefects(
    Number.isFinite(id) && id > 0 ? { page: 1, size: 5, test_execution_id: id } : undefined
  )

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center text-muted-foreground">加载中...</div>
  }

  if (!execution) {
    return <div className="py-16 text-center text-destructive">执行记录不存在</div>
  }

  const logs = execution.logs || []
  const stepLogs = logs.filter((item: any) => item?.type === 'step' || item?.step_index !== undefined)
  const otherLogs = logs.filter((item: any) => !(item?.type === 'step' || item?.step_index !== undefined))
  const canPause = execution.execution_status === ExecutionStatus.IN_PROGRESS
  const canResume = execution.execution_status === ExecutionStatus.BLOCKED
  const canCancel = execution.execution_status === ExecutionStatus.IN_PROGRESS || execution.execution_status === ExecutionStatus.BLOCKED
  const linkedDefects = linkedDefectsData?.data || []
  const canCreateDefect = execution.execution_status === ExecutionStatus.FAILED && linkedDefects.length === 0

  const handleCreateDefect = async () => {
    const defect = await createDefect.mutateAsync({
      title: `${execution.test_case_code || `用例 #${execution.test_case_id}`} 执行失败`,
      description: [
        `执行记录：${execution.execution_code}`,
        `测试用例：${execution.test_case_title || execution.test_case_code || execution.test_case_id}`,
        `失败原因：${execution.failure_reason || '未填写'}`,
        `实际结果：${execution.actual_result || '未填写'}`,
        `执行环境：${execution.test_environment || '-'}`,
      ].join('\n'),
      steps_to_reproduce: buildFailureSteps(stepLogs),
      defect_type: DefectType.FUNCTIONAL,
      severity: inferDefectSeverity(execution.test_case_priority),
      priority: (execution.test_case_priority as Priority) || Priority.MEDIUM,
      test_execution_id: execution.id,
      test_case_id: execution.test_case_id,
      test_environment: execution.test_environment,
      attachments: [
        ...(execution.screenshots || []),
        ...(execution.videos || []),
      ],
    })
    window.location.href = `/test-manager/defects?search=${encodeURIComponent(defect.defect_code || defect.title)}`
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link to="/test-manager/executions">
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回执行管理
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{execution.execution_code}</h1>
            <p className="text-sm text-muted-foreground">{execution.test_case_title || `用例 #${execution.test_case_id}`}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {canPause && (
            <Button variant="outline" onClick={() => pauseExecution.mutate(execution.id)}>
              <Pause className="mr-2 h-4 w-4" />
              暂停
            </Button>
          )}
          {canResume && (
            <Button variant="outline" onClick={() => resumeExecution.mutate(execution.id)}>
              <Play className="mr-2 h-4 w-4" />
              恢复
            </Button>
          )}
          {canCancel && (
            <Button variant="outline" onClick={() => cancelExecution.mutate(execution.id)}>
              <Square className="mr-2 h-4 w-4" />
              取消执行
            </Button>
          )}
          {execution.execution_type === ExecutionType.MANUAL && (
            <Button asChild>
              <Link to={`/test-manager/executions/manual/${execution.test_case_id}`}>重新执行该用例</Link>
            </Button>
          )}
          {execution.execution_status === ExecutionStatus.FAILED && (
            <Button
              variant={canCreateDefect ? 'default' : 'outline'}
              disabled={!canCreateDefect || createDefect.isPending}
              onClick={handleCreateDefect}
              title={linkedDefects.length > 0 ? '该执行记录已关联缺陷' : '根据失败执行创建缺陷'}
            >
              <Bug className="mr-2 h-4 w-4" />
              {linkedDefects.length > 0 ? '已关联缺陷' : createDefect.isPending ? '创建中...' : '转缺陷'}
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">状态</p>
            <div className="mt-2">
              <Badge variant={statusVariants[execution.execution_status] || 'secondary'}>
                {statusLabels[execution.execution_status] || execution.execution_status}
              </Badge>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">执行类型</p>
            <p className="mt-2 text-lg font-semibold">{execution.execution_type === ExecutionType.MANUAL ? '手工执行' : '自动化执行'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">执行环境</p>
            <p className="mt-2 text-lg font-semibold">{execution.test_environment || '-'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">耗时</p>
            <p className="mt-2 text-lg font-semibold">{formatDuration(execution.duration)}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">步骤执行结果</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">步骤</TableHead>
                    <TableHead>操作</TableHead>
                    <TableHead>预期结果</TableHead>
                    <TableHead>实际结果</TableHead>
                    <TableHead className="w-24">状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {stepLogs.length ? stepLogs.map((log: any, index: number) => (
                    <TableRow key={`${log.step_index}-${index}`}>
                      <TableCell>{Number(log.step_index ?? index) + 1}</TableCell>
                      <TableCell>{getStepText(log, 'action')}</TableCell>
                      <TableCell>{getStepText(log, 'expected_result')}</TableCell>
                      <TableCell>{getStepText(log, 'actual_result')}</TableCell>
                      <TableCell>
                        <Badge variant={statusVariants[log.status] || 'secondary'}>{statusLabels[log.status] || log.status || '-'}</Badge>
                      </TableCell>
                    </TableRow>
                  )) : (
                    <TableRow>
                      <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                        暂无步骤日志
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">执行结论</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">实际结果</p>
                <p className="mt-1 whitespace-pre-wrap">{execution.actual_result || '-'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">失败原因</p>
                <p className="mt-1 whitespace-pre-wrap">{execution.failure_reason || '-'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">执行备注</p>
                <p className="mt-1 whitespace-pre-wrap">{execution.execution_notes || '-'}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">基础信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between gap-3"><span className="text-muted-foreground">用例编号</span><span>{execution.test_case_code || execution.test_case_id}</span></div>
              <div className="flex justify-between gap-3"><span className="text-muted-foreground">优先级</span><span>{execution.test_case_priority || '-'}</span></div>
              <div className="flex justify-between gap-3"><span className="text-muted-foreground">执行人ID</span><span>{execution.executor_id}</span></div>
              <div className="flex justify-between gap-3"><span className="text-muted-foreground">浏览器</span><span>{execution.browser_info || '-'}</span></div>
              <div className="flex justify-between gap-3"><span className="text-muted-foreground">操作系统</span><span>{execution.os_info || '-'}</span></div>
              <div className="flex justify-between gap-3"><span className="text-muted-foreground">开始时间</span><span>{execution.started_at ? formatDate(execution.started_at) : '-'}</span></div>
              <div className="flex justify-between gap-3"><span className="text-muted-foreground">结束时间</span><span>{execution.completed_at ? formatDate(execution.completed_at) : '-'}</span></div>
            </CardContent>
          </Card>

          {linkedDefects.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">关联缺陷</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {linkedDefects.map((defect: any) => (
                  <Link key={defect.id} to={`/test-manager/defects?search=${encodeURIComponent(defect.defect_code)}`} className="block rounded border p-3 hover:bg-muted/40">
                    <div className="font-medium">{defect.title}</div>
                    <div className="mt-1 flex items-center justify-between gap-3 text-xs text-muted-foreground">
                      <span>{defect.defect_code}</span>
                      <Badge variant="secondary">{defect.status}</Badge>
                    </div>
                  </Link>
                ))}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5" />
                执行日志
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-72 rounded border bg-muted/30 p-3">
                {otherLogs.length ? otherLogs.map((log: any, index: number) => (
                  <pre key={index} className="mb-3 whitespace-pre-wrap text-xs">
                    {typeof log === 'string' ? log : JSON.stringify(log, null, 2)}
                  </pre>
                )) : (
                  <div className="text-sm text-muted-foreground">暂无其他日志</div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">附件</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-medium">截图</span>
                  <Badge variant="secondary">{execution.screenshots?.length || 0}</Badge>
                </div>
                {execution.screenshots?.length ? (
                  <div className="space-y-1">
                    {execution.screenshots.map((item: any, index: number) => (
                      <div key={`${item.file_path || item.filename}-${index}`} className="rounded bg-muted/40 px-2 py-1">
                        <div className="truncate">{item.filename || `截图 ${index + 1}`}</div>
                        <div className="text-xs text-muted-foreground">{formatFileSize(item.file_size)}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted-foreground">暂无截图</div>
                )}
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-medium">录像</span>
                  <Badge variant="secondary">{execution.videos?.length || 0}</Badge>
                </div>
                {execution.videos?.length ? (
                  <div className="space-y-1">
                    {execution.videos.map((item: any, index: number) => (
                      <div key={`${item.file_path || item.filename}-${index}`} className="rounded bg-muted/40 px-2 py-1">
                        <div className="truncate">{item.filename || `录像 ${index + 1}`}</div>
                        <div className="text-xs text-muted-foreground">{formatFileSize(item.file_size)}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted-foreground">暂无录像</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default ExecutionDetail
