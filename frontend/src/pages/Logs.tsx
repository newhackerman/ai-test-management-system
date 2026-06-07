// @ts-nocheck
import { useMemo, useState } from 'react';
import { AlertCircle, CheckCircle, Clock, Download, Filter, Info, Search, XCircle } from 'lucide-react';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';

type LogLevel = 'error' | 'warning' | 'info' | 'success';

interface LogItem {
  id: number;
  timestamp: string;
  level: LogLevel;
  source: string;
  message: string;
  user: string;
  ip: string;
}

const logs: LogItem[] = [
  {
    id: 1,
    timestamp: '2026-06-01 14:30:25',
    level: 'info',
    source: 'auth-service',
    message: '用户张三登录成功',
    user: 'zhangsan',
    ip: '192.168.1.100',
  },
  {
    id: 2,
    timestamp: '2026-06-01 14:25:10',
    level: 'error',
    source: 'api-gateway',
    message: '数据库连接失败，正在重试',
    user: 'system',
    ip: '127.0.0.1',
  },
  {
    id: 3,
    timestamp: '2026-06-01 14:20:05',
    level: 'warning',
    source: 'test-runner',
    message: '测试用例执行超时警告',
    user: 'lisi',
    ip: '192.168.1.101',
  },
  {
    id: 4,
    timestamp: '2026-06-01 14:15:30',
    level: 'info',
    source: 'project-service',
    message: '项目“AI 测试平台”已更新',
    user: 'wangwu',
    ip: '192.168.1.102',
  },
  {
    id: 5,
    timestamp: '2026-06-01 14:10:15',
    level: 'success',
    source: 'deployment',
    message: '系统更新部署完成',
    user: 'system',
    ip: '127.0.0.1',
  },
];

const levelMeta = {
  error: { label: '错误', variant: 'destructive', icon: <XCircle className="h-4 w-4 text-red-500" /> },
  warning: { label: '警告', variant: 'secondary', icon: <AlertCircle className="h-4 w-4 text-yellow-500" /> },
  info: { label: '信息', variant: 'default', icon: <Info className="h-4 w-4 text-blue-500" /> },
  success: { label: '成功', variant: 'default', icon: <CheckCircle className="h-4 w-4 text-green-500" /> },
};

export default function Logs() {
  const [keyword, setKeyword] = useState('');
  const [level, setLevel] = useState('all');
  const [source, setSource] = useState('all');
  const [timeRange, setTimeRange] = useState('24h');

  const filteredLogs = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return logs.filter((log) => {
      const keywordMatched =
        !normalizedKeyword ||
        `${log.message} ${log.source} ${log.user} ${log.ip}`.toLowerCase().includes(normalizedKeyword);
      const levelMatched = level === 'all' || log.level === level;
      const sourceMatched = source === 'all' || log.source === source;
      return keywordMatched && levelMatched && sourceMatched;
    });
  }, [keyword, level, source]);

  const stats = useMemo(
    () =>
      logs.reduce(
        (acc, log) => {
          acc[log.level] += 1;
          return acc;
        },
        { error: 0, warning: 0, info: 0, success: 0 } as Record<LogLevel, number>,
      ),
    [],
  );

  const exportLogs = () => {
    const csv = [
      ['时间', '级别', '服务', '消息', '用户', 'IP地址'],
      ...filteredLogs.map((log) => [log.timestamp, levelMeta[log.level].label, log.source, log.message, log.user, log.ip]),
    ]
      .map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(','))
      .join('\n');

    const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `system-logs-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">日志管理</h1>
          <p className="text-muted-foreground">查看系统运行日志、用户操作记录和错误信息。</p>
        </div>
        <Button onClick={exportLogs}>
          <Download className="mr-2 h-4 w-4" />
          导出日志
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>日志查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-4">
            <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索日志内容..." />
            <NativeSelect
              value={level}
              onChange={setLevel}
              placeholder="日志级别"
              options={[
                { value: 'all', label: '全部级别' },
                { value: 'error', label: '错误' },
                { value: 'warning', label: '警告' },
                { value: 'info', label: '信息' },
                { value: 'success', label: '成功' },
              ]}
            />
            <NativeSelect
              value={source}
              onChange={setSource}
              placeholder="服务模块"
              options={[
                { value: 'all', label: '全部服务' },
                { value: 'auth-service', label: '认证服务' },
                { value: 'api-gateway', label: 'API 网关' },
                { value: 'project-service', label: '项目服务' },
                { value: 'test-runner', label: '测试运行器' },
                { value: 'deployment', label: '部署服务' },
              ]}
            />
            <NativeSelect
              value={timeRange}
              onChange={setTimeRange}
              placeholder="时间范围"
              options={[
                { value: '1h', label: '最近 1 小时' },
                { value: '24h', label: '最近 24 小时' },
                { value: '7d', label: '最近 7 天' },
                { value: '30d', label: '最近 30 天' },
              ]}
            />
          </div>
          <div className="flex space-x-2">
            <Button>
              <Search className="mr-2 h-4 w-4" />
              查询
            </Button>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              高级筛选
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>日志列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>级别</TableHead>
                  <TableHead>服务</TableHead>
                  <TableHead>消息</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>IP 地址</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-mono text-sm">{log.timestamp}</TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        {levelMeta[log.level].icon}
                        <Badge variant={levelMeta[log.level].variant as any}>{levelMeta[log.level].label}</Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{log.source}</Badge>
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <div className="truncate" title={log.message}>
                        {log.message}
                      </div>
                    </TableCell>
                    <TableCell>{log.user}</TableCell>
                    <TableCell className="font-mono text-sm">{log.ip}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatCard icon={<XCircle className="h-8 w-8 text-red-500" />} value={stats.error} label="错误日志" />
        <StatCard icon={<AlertCircle className="h-8 w-8 text-yellow-500" />} value={stats.warning} label="警告日志" />
        <StatCard icon={<Info className="h-8 w-8 text-blue-500" />} value={stats.info} label="信息日志" />
        <StatCard icon={<CheckCircle className="h-8 w-8 text-green-500" />} value={stats.success} label="成功日志" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>实时日志监控</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-60 overflow-y-auto rounded-lg bg-black/90 p-4 font-mono text-sm text-green-400">
            <div className="space-y-1">
              <div>[2026-06-01 14:35:12] INFO auth-service: 用户登录请求 - IP: 192.168.1.103</div>
              <div>[2026-06-01 14:35:10] INFO api-gateway: API 请求转发 - /api/projects</div>
              <div>[2026-06-01 14:35:08] INFO test-runner: 测试用例执行开始 - ID: TC001</div>
              <div>[2026-06-01 14:35:05] SUCCESS deployment: 代码部署完成 - v1.2.3</div>
              <div>[2026-06-01 14:35:03] INFO project-service: 项目状态更新 - ID: PROJ001</div>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <span className="text-sm text-muted-foreground">实时监控已启用，显示最新日志。</span>
            <Button variant="outline" size="sm">
              暂停监控
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

const StatCard: React.FC<{ icon: React.ReactNode; value: number; label: string }> = ({ icon, value, label }) => (
  <Card>
    <CardContent className="p-6">
      <div className="flex items-center">
        {icon}
        <div className="ml-4">
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-sm text-muted-foreground">{label}</p>
        </div>
      </div>
    </CardContent>
  </Card>
);

const NativeSelect: React.FC<{
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  options: Array<{ value: string; label: string }>;
}> = ({ value, onChange, placeholder, options }) => (
  <select
    value={value}
    onChange={(event) => onChange(event.target.value)}
    aria-label={placeholder}
    className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
  >
    {options.map((option) => (
      <option key={option.value} value={option.value}>
        {option.label}
      </option>
    ))}
  </select>
);
