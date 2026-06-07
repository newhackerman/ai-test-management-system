import React from 'react';
import { Activity, CheckCircle, Clock, DollarSign, Server, Zap } from 'lucide-react';

import { Badge } from '../ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Progress } from '../ui/Progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/Table';
import { AIProviderStats } from '../../types/aiModelConfig';

interface AIProviderStatsCardProps {
  stats: AIProviderStats[];
}

export const AIProviderStatsCard: React.FC<AIProviderStatsCardProps> = ({ stats }) => {
  const total = stats.reduce(
    (acc, item) => ({
      total_models: acc.total_models + item.total_models,
      enabled_models: acc.enabled_models + item.enabled_models,
      default_models: acc.default_models + item.default_models,
      total_requests: acc.total_requests + item.total_requests,
      total_tokens: acc.total_tokens + item.total_tokens,
      total_cost: acc.total_cost + item.total_cost,
      avg_response_time: acc.avg_response_time + item.avg_response_time,
    }),
    {
      total_models: 0,
      enabled_models: 0,
      default_models: 0,
      total_requests: 0,
      total_tokens: 0,
      total_cost: 0,
      avg_response_time: 0,
    },
  );

  const enabledRate = total.total_models > 0 ? (total.enabled_models / total.total_models) * 100 : 0;
  const avgResponseTime = stats.length > 0 ? total.avg_response_time / stats.length : 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          icon={<Server className="h-4 w-4 text-muted-foreground" />}
          label="模型总数"
          value={total.total_models.toString()}
          description={`${total.enabled_models} 个已启用`}
        />
        <SummaryCard
          icon={<Activity className="h-4 w-4 text-muted-foreground" />}
          label="请求总数"
          value={total.total_requests.toLocaleString()}
          description="累计调用次数"
        />
        <SummaryCard
          icon={<Zap className="h-4 w-4 text-muted-foreground" />}
          label="Token 使用"
          value={total.total_tokens.toLocaleString()}
          description="累计消耗 Token"
        />
        <SummaryCard
          icon={<DollarSign className="h-4 w-4 text-muted-foreground" />}
          label="累计成本"
          value={`¥${total.total_cost.toFixed(4)}`}
          description={`平均响应 ${avgResponseTime.toFixed(2)}s`}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">供应商状态</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>启用率</span>
              <span>{enabledRate.toFixed(1)}%</span>
            </div>
            <Progress value={enabledRate} />
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>供应商</TableHead>
                <TableHead>模型</TableHead>
                <TableHead>默认</TableHead>
                <TableHead>请求</TableHead>
                <TableHead>Token</TableHead>
                <TableHead>成本</TableHead>
                <TableHead>平均响应</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stats.map((item) => (
                <TableRow key={item.provider}>
                  <TableCell className="font-medium">{item.provider}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{item.enabled_models}/{item.total_models}</Badge>
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    </div>
                  </TableCell>
                  <TableCell>{item.default_models}</TableCell>
                  <TableCell>{item.total_requests.toLocaleString()}</TableCell>
                  <TableCell>{item.total_tokens.toLocaleString()}</TableCell>
                  <TableCell>¥{item.total_cost.toFixed(4)}</TableCell>
                  <TableCell>
                    <span className="inline-flex items-center gap-1">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      {item.avg_response_time.toFixed(2)}s
                    </span>
                  </TableCell>
                </TableRow>
              ))}
              {stats.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">
                    暂无统计数据
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

interface SummaryCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  description: string;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ icon, label, value, description }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{label}</CardTitle>
      {icon}
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-semibold">{value}</div>
      <p className="text-xs text-muted-foreground">{description}</p>
    </CardContent>
  </Card>
);
