import React, { useMemo, useState } from 'react'
import { CheckCircle, FileText, Plus, Search, XCircle } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import type { ChangePriority, ChangeStatus, ChangeType, RequirementChangeRequest } from '@/types/requirement'

const initialChanges: RequirementChangeRequest[] = [
  {
    id: 1,
    requirement_id: 101,
    change_request_code: 'CR-2026-001',
    title: '增强登录安全策略',
    description: '补充密码修改后的会话刷新、最后登录和密码修改时间记录。',
    reason: '修复认证状态和安全审计信息不一致问题。',
    change_type: 'MODIFICATION' as ChangeType,
    impact_analysis: '影响登录、个人设置、安全设置模块。',
    effort_estimate: 2,
    status: 'UNDER_REVIEW' as ChangeStatus,
    priority: 'HIGH' as ChangePriority,
    requestor_id: 1,
    requested_date: '2026-06-01',
    target_date: '2026-06-03',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    requirement_id: 108,
    change_request_code: 'CR-2026-002',
    title: '统一用户与角色权限关联',
    description: '新增用户时需要立即绑定角色并支持权限查看。',
    reason: '避免新增用户没有角色和权限面板空白。',
    change_type: 'MODIFICATION' as ChangeType,
    impact_analysis: '影响用户管理、角色管理、权限查看。',
    effort_estimate: 3,
    status: 'APPROVED' as ChangeStatus,
    priority: 'EMERGENCY' as ChangePriority,
    requestor_id: 1,
    approver_id: 1,
    requested_date: '2026-06-01',
    approved_date: '2026-06-01',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
]

const statusText: Record<ChangeStatus, string> = {
  SUBMITTED: '已提交',
  UNDER_REVIEW: '评审中',
  APPROVED: '已批准',
  REJECTED: '已拒绝',
  IMPLEMENTED: '已实施',
  CLOSED: '已关闭',
}

const priorityText: Record<ChangePriority, string> = {
  EMERGENCY: '紧急',
  HIGH: '高',
  MEDIUM: '中',
  LOW: '低',
}

export default function RequirementChangeManagement() {
  const [changes, setChanges] = useState<RequirementChangeRequest[]>(initialChanges)
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<ChangeStatus | 'ALL'>('ALL')

  const filteredChanges = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    return changes.filter((change) => {
      const matchesKeyword =
        !normalized ||
        change.title.toLowerCase().includes(normalized) ||
        change.change_request_code.toLowerCase().includes(normalized) ||
        change.description.toLowerCase().includes(normalized)
      const matchesStatus = status === 'ALL' || change.status === status
      return matchesKeyword && matchesStatus
    })
  }, [changes, keyword, status])

  const updateStatus = (id: number, nextStatus: ChangeStatus) => {
    setChanges((current) =>
      current.map((change) =>
        change.id === id
          ? { ...change, status: nextStatus, updated_at: new Date().toISOString() }
          : change,
      ),
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">需求变更管理</h1>
        </div>
        <Button type="button">
          <Plus className="mr-2 h-4 w-4" />
          新建变更
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Stat title="全部变更" value={changes.length} />
        <Stat title="评审中" value={changes.filter((item) => item.status === 'UNDER_REVIEW').length} />
        <Stat title="已批准" value={changes.filter((item) => item.status === 'APPROVED').length} />
        <Stat title="已实施" value={changes.filter((item) => item.status === 'IMPLEMENTED').length} />
      </div>

      <Card>
        <CardContent className="flex flex-col gap-3 p-4 md:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索变更单" className="pl-9" />
          </div>
          <select value={status} onChange={(event) => setStatus(event.target.value as ChangeStatus | 'ALL')} className="h-10 rounded-md border bg-background px-3 text-sm">
            <option value="ALL">全部状态</option>
            <option value="SUBMITTED">已提交</option>
            <option value="UNDER_REVIEW">评审中</option>
            <option value="APPROVED">已批准</option>
            <option value="REJECTED">已拒绝</option>
            <option value="IMPLEMENTED">已实施</option>
            <option value="CLOSED">已关闭</option>
          </select>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {filteredChanges.map((change) => (
          <Card key={change.id}>
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  <div>
                    <CardTitle className="text-lg">{change.title}</CardTitle>
                    <p className="text-xs text-muted-foreground">{change.change_request_code}</p>
                  </div>
                </div>
                <Badge variant={change.priority === 'EMERGENCY' ? 'destructive' : 'outline'}>
                  {priorityText[change.priority]}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">{change.description}</p>
              <div className="flex flex-wrap gap-2">
                <Badge>{statusText[change.status]}</Badge>
                <Badge variant="outline">需求 #{change.requirement_id}</Badge>
                <Badge variant="outline">工作量 {change.effort_estimate ?? '-'} 天</Badge>
              </div>
              {change.impact_analysis && (
                <div className="rounded-md bg-muted p-3 text-sm">影响分析：{change.impact_analysis}</div>
              )}
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => updateStatus(change.id, 'REJECTED' as ChangeStatus)}>
                  <XCircle className="mr-2 h-4 w-4" />
                  拒绝
                </Button>
                <Button type="button" onClick={() => updateStatus(change.id, 'APPROVED' as ChangeStatus)}>
                  <CheckCircle className="mr-2 h-4 w-4" />
                  批准
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

const Stat = ({ title, value }: { title: string; value: number }) => (
  <Card>
    <CardContent className="p-4">
      <div className="text-sm text-muted-foreground">{title}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </CardContent>
  </Card>
)
