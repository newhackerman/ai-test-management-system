import { Activity, AlertTriangle, CheckCircle, Clock, Cpu, Database, Eye, HardDrive, Search, TrendingUp, Wifi, XCircle, Zap } from 'lucide-react'

import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table'

type SystemMetric = {
  label: string
  status: 'normal' | 'warning' | 'error'
  icon: typeof Cpu
  color: string
  usage?: number
  latency?: number
}

const formatDateTime = (value: string) =>
  new Date(value).toLocaleString('zh-CN', {
    hour12: false,
    timeZone: 'Asia/Shanghai',
  })

export default function Monitoring() {
  const systemMetrics: Record<string, SystemMetric> = {
    cpu: { label: 'CPU 使用率', usage: 45, status: 'normal', icon: Cpu, color: 'text-blue-500' },
    memory: { label: '内存使用率', usage: 62, status: 'warning', icon: Database, color: 'text-green-500' },
    disk: { label: '磁盘使用率', usage: 23, status: 'normal', icon: HardDrive, color: 'text-purple-500' },
    network: { label: '网络延迟', latency: 23, status: 'normal', icon: Wifi, color: 'text-orange-500' },
  }

  const services = [
    { name: 'API 网关', status: 'running', uptime: '99.9%', responseTime: '120ms', lastChecked: '2026-06-01T14:30:00+08:00' },
    { name: '认证服务', status: 'running', uptime: '99.7%', responseTime: '89ms', lastChecked: '2026-06-01T14:30:00+08:00' },
    { name: '数据库', status: 'running', uptime: '99.5%', responseTime: '45ms', lastChecked: '2026-06-01T14:30:00+08:00' },
    { name: '测试执行器', status: 'warning', uptime: '98.2%', responseTime: '234ms', lastChecked: '2026-06-01T14:30:00+08:00' },
  ]

  const alerts = [
    { id: 1, level: 'critical', message: '数据库连接池达到上限', source: 'database', timestamp: '2026-06-01T14:25:00+08:00', status: 'active' },
    { id: 2, level: 'warning', message: '内存使用率超过 60%', source: 'system', timestamp: '2026-06-01T14:20:00+08:00', status: 'active' },
    { id: 3, level: 'info', message: '系统更新已完成', source: 'deployment', timestamp: '2026-06-01T14:15:00+08:00', status: 'resolved' },
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
      case 'normal':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    const statusMap = {
      running: { label: '正常', variant: 'default' as const },
      warning: { label: '警告', variant: 'secondary' as const },
      error: { label: '错误', variant: 'destructive' as const },
    }
    const statusInfo = statusMap[status as keyof typeof statusMap] || { label: status, variant: 'outline' as const }
    return <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
  }

  const getAlertLevelBadge = (level: string) => {
    const levelMap = {
      critical: { label: '严重', variant: 'destructive' as const },
      warning: { label: '警告', variant: 'secondary' as const },
      info: { label: '信息', variant: 'outline' as const },
    }
    const levelInfo = levelMap[level as keyof typeof levelMap] || { label: level, variant: 'outline' as const }
    return <Badge variant={levelInfo.variant}>{levelInfo.label}</Badge>
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">监控告警</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline">
            <Activity className="mr-2 h-4 w-4" />
            刷新数据
          </Button>
          <Button variant="outline" onClick={() => (window.location.href = '/lighthouse-performance')}>
            <Zap className="mr-2 h-4 w-4" />
            Lighthouse 性能分析
          </Button>
          <Button>
            <AlertTriangle className="mr-2 h-4 w-4" />
            配置告警
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Object.entries(systemMetrics).map(([key, metric]) => {
          const Icon = metric.icon
          const value = key === 'network' ? metric.latency ?? 0 : metric.usage ?? 0
          const progress = key === 'network' ? Math.min((metric.latency ?? 0) / 2, 100) : metric.usage ?? 0

          return (
            <Card key={key}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Icon className={`h-8 w-8 ${metric.color}`} />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-muted-foreground">{metric.label}</p>
                      <p className="text-2xl font-bold">
                        {value}
                        {key === 'network' ? 'ms' : '%'}
                      </p>
                    </div>
                  </div>
                  {getStatusIcon(metric.status)}
                </div>
                <div className="mt-4">
                  <Progress value={progress} className="h-2" />
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>服务状态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {services.map((service) => (
              <div key={service.name} className="flex items-center justify-between rounded-lg border p-4">
                <div className="flex items-center gap-4">
                  {getStatusIcon(service.status)}
                  <div>
                    <h3 className="font-medium">{service.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      可用性：{service.uptime} | 响应时间：{service.responseTime}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  {getStatusBadge(service.status)}
                  <p className="mt-1 text-xs text-muted-foreground">最后检查：{formatDateTime(service.lastChecked)}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>告警信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>级别</TableHead>
                  <TableHead>消息</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead>时间</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts.map((alert) => (
                  <TableRow key={alert.id}>
                    <TableCell>{getAlertLevelBadge(alert.level)}</TableCell>
                    <TableCell className="max-w-xs">
                      <div className="truncate" title={alert.message}>
                        {alert.message}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{alert.source}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{formatDateTime(alert.timestamp)}</TableCell>
                    <TableCell>
                      <Badge variant={alert.status === 'active' ? 'destructive' : 'default'}>
                        {alert.status === 'active' ? '未处理' : '已解决'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm">查看</Button>
                        {alert.status === 'active' && <Button variant="ghost" size="sm">解决</Button>}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Web 性能监控</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[
              [Zap, 'Lighthouse Performance', 'Ready', 'text-blue-500'],
              [Clock, 'Page Load', '< 2s', 'text-green-500'],
              [Eye, 'Accessibility', '95+', 'text-purple-500'],
              [Search, 'SEO', 'Good', 'text-orange-500'],
            ].map(([Icon, label, value, color]) => (
              <div key={label as string} className="rounded-lg border p-4 text-center">
                <Icon className={`mx-auto mb-2 h-8 w-8 ${color}`} />
                <p className="text-sm font-medium text-muted-foreground">{label as string}</p>
                <p className="text-2xl font-bold">{value as string}</p>
              </div>
            ))}
          </div>
          <div className="flex justify-center">
            <Button onClick={() => (window.location.href = '/lighthouse-performance')}>
              <Zap className="mr-2 h-4 w-4" />
              开始性能分析
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>性能趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-64 items-center justify-center rounded-lg border-2 border-dashed border-gray-300">
            <div className="text-center">
              <TrendingUp className="mx-auto mb-2 h-12 w-12 text-gray-400" />
              <p className="text-muted-foreground">暂无性能趋势数据</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
