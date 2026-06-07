import React, { useMemo, useState } from 'react'
import { BarChart3, Download, RefreshCw, TrendingUp, Users } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'

interface TimeSeriesData {
  date: string
  requests: number
  tokens: number
  cost: number
  responseTime: number
}

interface ModelUsageData {
  name: string
  requests: number
  cost: number
}

interface UserActivityData {
  name: string
  requests: number
  tokens: number
}

const colors = ['#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#7c3aed']

const createTimeSeries = (days: number): TimeSeriesData[] =>
  Array.from({ length: days }, (_, index) => {
    const date = new Date()
    date.setDate(date.getDate() - (days - index - 1))
    return {
      date: `${date.getMonth() + 1}/${date.getDate()}`,
      requests: 80 + index * 11 + (index % 3) * 18,
      tokens: 12000 + index * 850,
      cost: Number((10 + index * 1.8).toFixed(2)),
      responseTime: Number((0.8 + (index % 4) * 0.15).toFixed(2)),
    }
  })

const modelData: ModelUsageData[] = [
  { name: 'GPT-4', requests: 420, cost: 82.4 },
  { name: 'GPT-4o mini', requests: 680, cost: 24.7 },
  { name: 'Claude', requests: 260, cost: 46.2 },
  { name: 'Qwen', requests: 310, cost: 18.9 },
]

const userData: UserActivityData[] = [
  { name: '测试经理', requests: 320, tokens: 86000 },
  { name: '测试工程师', requests: 510, tokens: 133000 },
  { name: '需求分析', requests: 210, tokens: 58000 },
  { name: '开发人员', requests: 190, tokens: 47000 },
]

const UsageStatisticsCharts: React.FC = () => {
  const [range, setRange] = useState(7)
  const [refreshing, setRefreshing] = useState(false)
  const timeSeries = useMemo(() => createTimeSeries(range), [range])

  const totalRequests = timeSeries.reduce((sum, item) => sum + item.requests, 0)
  const totalTokens = timeSeries.reduce((sum, item) => sum + item.tokens, 0)
  const totalCost = timeSeries.reduce((sum, item) => sum + item.cost, 0)
  const avgResponse = timeSeries.reduce((sum, item) => sum + item.responseTime, 0) / timeSeries.length

  const refresh = () => {
    setRefreshing(true)
    window.setTimeout(() => setRefreshing(false), 400)
  }

  const exportData = () => {
    const payload = JSON.stringify({ timeSeries, modelData, userData }, null, 2)
    const blob = new Blob([payload], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'usage-statistics.json'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">AI 用量统计</h2>
          <p className="text-sm text-muted-foreground">查看请求量、Token、费用和模型使用趋势。</p>
        </div>
        <div className="flex gap-2">
          <select value={range} onChange={(event) => setRange(Number(event.target.value))} className="h-10 rounded-md border bg-background px-3 text-sm">
            <option value={7}>近 7 天</option>
            <option value={14}>近 14 天</option>
            <option value={30}>近 30 天</option>
          </select>
          <Button type="button" variant="outline" onClick={refresh} disabled={refreshing}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button type="button" variant="outline" onClick={exportData}>
            <Download className="mr-2 h-4 w-4" />
            导出
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <MetricCard title="请求量" value={totalRequests.toLocaleString()} icon={BarChart3} />
        <MetricCard title="Token" value={totalTokens.toLocaleString()} icon={TrendingUp} />
        <MetricCard title="费用" value={`$${totalCost.toFixed(2)}`} icon={Download} />
        <MetricCard title="平均响应" value={`${avgResponse.toFixed(2)}s`} icon={Users} />
      </div>

      <Tabs defaultValue="trend">
        <TabsList>
          <TabsTrigger value="trend">趋势</TabsTrigger>
          <TabsTrigger value="models">模型</TabsTrigger>
          <TabsTrigger value="users">用户</TabsTrigger>
        </TabsList>
        <TabsContent value="trend" className="mt-4">
          <Card>
            <CardHeader><CardTitle className="text-lg">请求趋势</CardTitle></CardHeader>
            <CardContent className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timeSeries}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="requests" stroke="#2563eb" strokeWidth={2} name="请求量" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="models" className="mt-4">
          <Card>
            <CardHeader><CardTitle className="text-lg">模型使用分布</CardTitle></CardHeader>
            <CardContent className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={modelData} dataKey="requests" nameKey="name" outerRadius={110} label>
                    {modelData.map((_, index) => <Cell key={index} fill={colors[index % colors.length]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="users" className="mt-4">
          <Card>
            <CardHeader><CardTitle className="text-lg">用户活跃度</CardTitle></CardHeader>
            <CardContent className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={userData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="requests" fill="#16a34a" name="请求量" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

const MetricCard = ({
  title,
  value,
  icon: Icon,
}: {
  title: string
  value: string
  icon: React.ComponentType<{ className?: string }>
}) => (
  <Card>
    <CardContent className="flex items-center justify-between p-4">
      <div>
        <div className="text-sm text-muted-foreground">{title}</div>
        <div className="text-2xl font-semibold">{value}</div>
      </div>
      <Icon className="h-8 w-8 text-muted-foreground" />
    </CardContent>
  </Card>
)

export default UsageStatisticsCharts
