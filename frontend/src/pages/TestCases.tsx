import React, { useMemo, useState } from 'react'
import { CheckCircle, Clock, Play, Plus, Search, XCircle } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'

interface TestCase {
  id: string
  name: string
  description: string
  status: 'passed' | 'failed' | 'pending' | 'skipped'
  priority: 'high' | 'medium' | 'low'
  project: string
  category: string
  lastRun: string
  duration: string
  author: string
  tags: string[]
}

const initialTestCases: TestCase[] = [
  {
    id: 'TC-001',
    name: '用户登录功能测试',
    description: '验证正常登录、错误密码、退出登录后的访问拦截。',
    status: 'passed',
    priority: 'high',
    project: '认证与权限',
    category: '功能测试',
    lastRun: '今天',
    duration: '2m 34s',
    author: '测试经理',
    tags: ['登录', '认证', '安全'],
  },
  {
    id: 'TC-002',
    name: '用户角色关联测试',
    description: '验证新增用户后角色、权限和查看权限面板正确展示。',
    status: 'pending',
    priority: 'high',
    project: '用户管理',
    category: '集成测试',
    lastRun: '未执行',
    duration: '-',
    author: '测试工程师',
    tags: ['用户', '角色', '权限'],
  },
  {
    id: 'TC-003',
    name: '系统设置保存测试',
    description: '验证消息通知、主题切换和系统参数修改后能持久化。',
    status: 'failed',
    priority: 'medium',
    project: '系统设置',
    category: '回归测试',
    lastRun: '昨天',
    duration: '4m 10s',
    author: '测试工程师',
    tags: ['设置', '通知', '主题'],
  },
]

const statusText: Record<TestCase['status'], string> = {
  passed: '通过',
  failed: '失败',
  pending: '待执行',
  skipped: '跳过',
}

const priorityText: Record<TestCase['priority'], string> = {
  high: '高',
  medium: '中',
  low: '低',
}

export default function TestCases() {
  const [testCases, setTestCases] = useState<TestCase[]>(initialTestCases)
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<TestCase['status'] | 'all'>('all')

  const filteredCases = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    return testCases.filter((testCase) => {
      const matchesKeyword =
        !normalized ||
        testCase.name.toLowerCase().includes(normalized) ||
        testCase.description.toLowerCase().includes(normalized) ||
        testCase.tags.some((tag) => tag.toLowerCase().includes(normalized))
      const matchesStatus = status === 'all' || testCase.status === status
      return matchesKeyword && matchesStatus
    })
  }, [keyword, status, testCases])

  const runCase = (id: string) => {
    setTestCases((current) =>
      current.map((testCase) =>
        testCase.id === id
          ? { ...testCase, status: 'passed', lastRun: '刚刚', duration: '1m 20s' }
          : testCase,
      ),
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">测试用例</h1>
        </div>
        <Button type="button">
          <Plus className="mr-2 h-4 w-4" />
          新建用例
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Stat title="全部用例" value={testCases.length} />
        <Stat title="通过" value={testCases.filter((item) => item.status === 'passed').length} />
        <Stat title="失败" value={testCases.filter((item) => item.status === 'failed').length} />
        <Stat title="待执行" value={testCases.filter((item) => item.status === 'pending').length} />
      </div>

      <Card>
        <CardContent className="flex flex-col gap-3 p-4 md:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索用例名称、描述或标签" className="pl-9" />
          </div>
          <select value={status} onChange={(event) => setStatus(event.target.value as TestCase['status'] | 'all')} className="h-10 rounded-md border bg-background px-3 text-sm">
            <option value="all">全部状态</option>
            <option value="passed">通过</option>
            <option value="failed">失败</option>
            <option value="pending">待执行</option>
            <option value="skipped">跳过</option>
          </select>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {filteredCases.map((testCase) => (
          <Card key={testCase.id}>
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle className="text-lg">{testCase.name}</CardTitle>
                  <p className="mt-1 text-xs text-muted-foreground">{testCase.id} · {testCase.project} · {testCase.category}</p>
                </div>
                <Badge variant={testCase.status === 'failed' ? 'destructive' : 'outline'}>
                  {statusText[testCase.status]}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">{testCase.description}</p>
              <div className="flex flex-wrap gap-2">
                <Badge variant={testCase.priority === 'high' ? 'destructive' : 'outline'}>优先级：{priorityText[testCase.priority]}</Badge>
                <Badge variant="outline">最近执行：{testCase.lastRun}</Badge>
                <Badge variant="outline">耗时：{testCase.duration}</Badge>
                {testCase.tags.map((tag) => <Badge key={tag} variant="secondary">{tag}</Badge>)}
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" disabled={testCase.status === 'passed'}>
                  {testCase.status === 'failed' ? <XCircle className="mr-2 h-4 w-4" /> : <Clock className="mr-2 h-4 w-4" />}
                  {statusText[testCase.status]}
                </Button>
                <Button type="button" onClick={() => runCase(testCase.id)}>
                  {testCase.status === 'passed' ? <CheckCircle className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
                  执行
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
