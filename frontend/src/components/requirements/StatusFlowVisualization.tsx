import React, { useMemo, useState } from 'react';
import { ArrowRight, CheckCircle2, Circle, RotateCcw } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { cn } from '@/lib/utils';
import type { Requirement, RequirementStatus } from '@/types/requirement';

const STATUS_FLOW_RULES: Record<RequirementStatus, RequirementStatus[]> = {
  DRAFT: ['PENDING_REVIEW', 'CANCELLED'],
  PENDING_REVIEW: ['REVIEWING', 'DRAFT', 'CANCELLED'],
  REVIEWING: ['APPROVED', 'NEEDS_REVISION', 'CANCELLED'],
  NEEDS_REVISION: ['PENDING_REVIEW', 'CANCELLED'],
  APPROVED: ['IN_DEVELOPMENT', 'CANCELLED'],
  IN_DEVELOPMENT: ['TESTING', 'PAUSED', 'NEEDS_REVISION'],
  PAUSED: ['IN_DEVELOPMENT', 'CANCELLED'],
  TESTING: ['COMPLETED', 'NEEDS_REVISION', 'TEST_FAILED'],
  TEST_FAILED: ['IN_DEVELOPMENT', 'CANCELLED'],
  COMPLETED: ['DEPLOYED', 'NEEDS_REVISION'],
  DEPLOYED: ['CLOSED'],
  CLOSED: ['DRAFT'],
  CANCELLED: ['DRAFT']
};

const statusOrder: RequirementStatus[] = [
  'DRAFT',
  'PENDING_REVIEW',
  'REVIEWING',
  'NEEDS_REVISION',
  'APPROVED',
  'IN_DEVELOPMENT',
  'PAUSED',
  'TESTING',
  'TEST_FAILED',
  'COMPLETED',
  'DEPLOYED',
  'CLOSED',
  'CANCELLED'
];

const STATUS_CONFIG: Record<RequirementStatus, { label: string; className: string; description: string }> = {
  DRAFT: { label: '草稿', className: 'bg-gray-100 text-gray-700', description: '需求刚创建，可继续补充内容。' },
  PENDING_REVIEW: { label: '待评审', className: 'bg-yellow-100 text-yellow-700', description: '需求已提交，等待评审。' },
  REVIEWING: { label: '评审中', className: 'bg-blue-100 text-blue-700 dark:text-blue-300 dark:bg-blue-900/30', description: '评审人员正在确认需求内容。' },
  NEEDS_REVISION: { label: '需修改', className: 'bg-orange-100 text-orange-700 dark:text-orange-400', description: '评审发现问题，需要修改后再次提交。' },
  APPROVED: { label: '已批准', className: 'bg-green-100 text-green-700', description: '需求通过评审，可以进入实现。' },
  IN_DEVELOPMENT: { label: '开发中', className: 'bg-purple-100 text-purple-700 dark:text-purple-400', description: '需求正在开发实现。' },
  PAUSED: { label: '已暂停', className: 'bg-slate-100 text-slate-700', description: '需求暂时停止推进。' },
  TESTING: { label: '测试中', className: 'bg-indigo-100 text-indigo-700 dark:text-indigo-300', description: '实现完成，正在测试验证。' },
  TEST_FAILED: { label: '测试失败', className: 'bg-red-100 text-red-700 dark:text-red-400 dark:bg-red-900/30', description: '测试发现问题，需要回到开发。' },
  COMPLETED: { label: '已完成', className: 'bg-emerald-100 text-emerald-700 dark:text-emerald-400', description: '开发和测试均已完成。' },
  DEPLOYED: { label: '已上线', className: 'bg-teal-100 text-teal-700', description: '需求已部署到目标环境。' },
  CLOSED: { label: '已关闭', className: 'bg-zinc-100 text-zinc-700', description: '需求生命周期结束。' },
  CANCELLED: { label: '已取消', className: 'bg-red-100 text-red-700 dark:text-red-400 dark:bg-red-900/30', description: '需求已取消，不再实现。' }
};

interface StatusFlowVisualizationProps {
  requirement?: Requirement;
  currentStatus?: RequirementStatus;
  onStatusChange?: (newStatus: RequirementStatus) => void;
  readOnly?: boolean;
  showAllStates?: boolean;
  className?: string;
}

export const StatusFlowVisualization: React.FC<StatusFlowVisualizationProps> = ({
  requirement,
  currentStatus,
  onStatusChange,
  readOnly = false,
  showAllStates = false,
  className
}) => {
  const [selectedStatus, setSelectedStatus] = useState<RequirementStatus | null>(null);
  const status = currentStatus || requirement?.status || 'DRAFT';
  const availableTransitions = STATUS_FLOW_RULES[status] || [];

  const visibleStatuses = useMemo(() => {
    if (showAllStates) return statusOrder;
    const relevant = new Set<RequirementStatus>([status, ...availableTransitions]);
    return statusOrder.filter((item) => relevant.has(item));
  }, [availableTransitions, showAllStates, status]);

  const handleStatusClick = (targetStatus: RequirementStatus) => {
    if (readOnly || targetStatus === status || !availableTransitions.includes(targetStatus)) return;
    setSelectedStatus(targetStatus);
    onStatusChange?.(targetStatus);
  };

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          状态流转图
          {requirement && <Badge variant="outline">{requirement.requirement_code}</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="rounded-lg border bg-muted/40 p-4">
          <div className="mb-2 text-sm text-muted-foreground">当前状态</div>
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
            <Badge className={cn('border-0', STATUS_CONFIG[status].className)}>{STATUS_CONFIG[status].label}</Badge>
            <span className="text-sm text-muted-foreground">{STATUS_CONFIG[status].description}</span>
          </div>
        </div>

        <div className="space-y-3">
          <div className="text-sm font-medium text-muted-foreground">可见状态</div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {visibleStatuses.map((targetStatus) => {
              const config = STATUS_CONFIG[targetStatus];
              const isCurrent = targetStatus === status;
              const canChange = !readOnly && availableTransitions.includes(targetStatus);
              return (
                <Button
                  key={targetStatus}
                  type="button"
                  variant={isCurrent ? 'default' : canChange ? 'secondary' : 'outline'}
                  className={cn('h-auto justify-start gap-2 p-3 text-left', !isCurrent && !canChange && 'opacity-60')}
                  disabled={!isCurrent && !canChange}
                  onClick={() => handleStatusClick(targetStatus)}
                  title={config.description}
                >
                  {isCurrent ? <CheckCircle2 className="h-4 w-4" /> : canChange ? <ArrowRight className="h-4 w-4" /> : <Circle className="h-4 w-4" />}
                  <span>
                    <span className="block font-medium">{config.label}</span>
                    <span className="block text-xs opacity-70">{targetStatus}</span>
                  </span>
                </Button>
              );
            })}
          </div>
        </div>

        {!readOnly && availableTransitions.length > 0 && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 dark:bg-blue-900/20">
            <div className="mb-2 text-sm font-medium text-blue-900 dark:text-blue-100">可执行的状态变更</div>
            <div className="flex flex-wrap gap-2">
              {availableTransitions.map((nextStatus) => (
                <Badge
                  key={nextStatus}
                  variant="secondary"
                  className="cursor-pointer hover:bg-blue-200"
                  onClick={() => handleStatusClick(nextStatus)}
                >
                  {STATUS_CONFIG[nextStatus]?.label || nextStatus}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {selectedStatus && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <RotateCcw className="h-4 w-4" />
            已选择流转到：{STATUS_CONFIG[selectedStatus].label}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default StatusFlowVisualization;
