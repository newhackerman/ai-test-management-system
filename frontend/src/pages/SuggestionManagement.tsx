import React, { useMemo, useState } from 'react'
import { CheckCircle, Lightbulb, Search, XCircle } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import type { Suggestion, SuggestionPriority, SuggestionStatus, SuggestionType } from '@/types/ai-assistant'

const initialSuggestions: Suggestion[] = [
  {
    id: 1,
    title: '补充边界值测试',
    description: '登录、用户管理和角色权限模块建议增加边界值和异常路径用例。',
    type: 'QUALITY_ENHANCEMENT' as SuggestionType,
    status: 'PENDING' as SuggestionStatus,
    priority: 'HIGH' as SuggestionPriority,
    user_id: 1,
    expected_benefit: '降低权限和认证回归风险',
    estimated_effort: '1 天',
    confidence_score: 0.91,
    created_at: new Date().toISOString(),
  },
  {
    id: 2,
    title: '统一接口参数映射',
    description: '用户、角色、系统设置接口需要统一前后端字段命名和空值处理策略。',
    type: 'PROCESS_IMPROVEMENT' as SuggestionType,
    status: 'ACCEPTED' as SuggestionStatus,
    priority: 'CRITICAL' as SuggestionPriority,
    user_id: 1,
    expected_benefit: '减少参数不一致导致的功能不可用',
    estimated_effort: '2 天',
    confidence_score: 0.96,
    created_at: new Date().toISOString(),
  },
]

const statusText: Record<SuggestionStatus, string> = {
  PENDING: '待处理',
  ACCEPTED: '已接受',
  REJECTED: '已拒绝',
  IMPLEMENTED: '已实施',
  CANCELLED: '已取消',
}

const priorityText: Record<SuggestionPriority, string> = {
  LOW: '低',
  MEDIUM: '中',
  HIGH: '高',
  CRITICAL: '严重',
}

export default function SuggestionManagement() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>(initialSuggestions)
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<SuggestionStatus | 'ALL'>('ALL')

  const filteredSuggestions = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    return suggestions.filter((suggestion) => {
      const matchesKeyword =
        !normalized ||
        suggestion.title.toLowerCase().includes(normalized) ||
        suggestion.description.toLowerCase().includes(normalized)
      const matchesStatus = status === 'ALL' || suggestion.status === status
      return matchesKeyword && matchesStatus
    })
  }, [keyword, status, suggestions])

  const updateStatus = (id: number, nextStatus: SuggestionStatus) => {
    setSuggestions((current) =>
      current.map((suggestion) =>
        suggestion.id === id
          ? { ...suggestion, status: nextStatus, updated_at: new Date().toISOString() }
          : suggestion,
      ),
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">建议管理</h1>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Stat title="全部建议" value={suggestions.length} />
        <Stat title="待处理" value={suggestions.filter((item) => item.status === 'PENDING').length} />
        <Stat title="已接受" value={suggestions.filter((item) => item.status === 'ACCEPTED').length} />
        <Stat title="已实施" value={suggestions.filter((item) => item.status === 'IMPLEMENTED').length} />
      </div>

      <Card>
        <CardContent className="flex flex-col gap-3 p-4 md:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索建议" className="pl-9" />
          </div>
          <select value={status} onChange={(event) => setStatus(event.target.value as SuggestionStatus | 'ALL')} className="h-10 rounded-md border bg-background px-3 text-sm">
            <option value="ALL">全部状态</option>
            <option value="PENDING">待处理</option>
            <option value="ACCEPTED">已接受</option>
            <option value="REJECTED">已拒绝</option>
            <option value="IMPLEMENTED">已实施</option>
            <option value="CANCELLED">已取消</option>
          </select>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {filteredSuggestions.map((suggestion) => (
          <Card key={suggestion.id}>
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Lightbulb className="h-5 w-5 text-primary" />
                  <CardTitle className="text-lg">{suggestion.title}</CardTitle>
                </div>
                <Badge variant={suggestion.priority === 'CRITICAL' ? 'destructive' : 'outline'}>
                  {priorityText[suggestion.priority]}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">{suggestion.description}</p>
              <div className="flex flex-wrap gap-2">
                <Badge>{statusText[suggestion.status]}</Badge>
                <Badge variant="outline">置信度 {Math.round((suggestion.confidence_score || 0) * 100)}%</Badge>
                {suggestion.estimated_effort && <Badge variant="outline">工作量 {suggestion.estimated_effort}</Badge>}
              </div>
              {suggestion.expected_benefit && (
                <div className="rounded-md bg-muted p-3 text-sm">{suggestion.expected_benefit}</div>
              )}
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => updateStatus(suggestion.id, 'REJECTED' as SuggestionStatus)}>
                  <XCircle className="mr-2 h-4 w-4" />
                  拒绝
                </Button>
                <Button type="button" onClick={() => updateStatus(suggestion.id, 'ACCEPTED' as SuggestionStatus)}>
                  <CheckCircle className="mr-2 h-4 w-4" />
                  接受
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
