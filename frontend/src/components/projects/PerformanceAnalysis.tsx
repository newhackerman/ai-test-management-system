import React, { useEffect, useState } from 'react';
import { Activity, AlertTriangle, Clock, Target, TrendingUp, Users } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import { cn } from '@/lib/utils';

interface PerformanceAnalysisProps {
  projectId: number;
  className?: string;
}

interface MetricState {
  overallProgress: number;
  healthScore: number;
  taskProgress: number;
  qualityScore: number;
  teamEfficiency: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export const PerformanceAnalysis: React.FC<PerformanceAnalysisProps> = ({ projectId, className }) => {
  const [metrics, setMetrics] = useState<MetricState>({
    overallProgress: 0,
    healthScore: 0,
    taskProgress: 0,
    qualityScore: 0,
    teamEfficiency: 0,
    riskLevel: 'LOW',
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/v1/project-statistics/projects/${projectId}/performance`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('load failed')))
      .then((data) => {
        if (cancelled) return;
        setMetrics({
          overallProgress: Number(data.overallProgress ?? data.overall_progress ?? 0),
          healthScore: Number(data.healthScore ?? data.health_score ?? 0),
          taskProgress: Number(data.taskProgress?.progressRate ?? data.task_progress?.progress_rate ?? 0),
          qualityScore: Number(data.qualityProgress?.progressRate ?? data.quality_progress?.quality_score ?? 0),
          teamEfficiency: Number(data.teamPerformance?.utilizationRate ?? data.team_performance?.utilization_rate ?? 0),
          riskLevel: data.riskLevel ?? data.risk_level ?? 'LOW',
        });
      })
      .catch(() => {
        if (!cancelled) setError('性能数据暂时不可用，已显示默认指标');
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  return (
    <div className={cn('space-y-4', className)}>
      {error && (
        <Alert className="border-orange-200 bg-orange-50 text-orange-700">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard icon={<TrendingUp className="h-4 w-4" />} label="整体进度" value={metrics.overallProgress} suffix="%" />
        <MetricCard icon={<Activity className="h-4 w-4" />} label="健康分" value={metrics.healthScore} />
        <MetricCard icon={<Target className="h-4 w-4" />} label="任务进度" value={metrics.taskProgress} suffix="%" />
        <MetricCard icon={<Clock className="h-4 w-4" />} label="质量得分" value={metrics.qualityScore} suffix="%" />
        <MetricCard icon={<Users className="h-4 w-4" />} label="团队效率" value={metrics.teamEfficiency} suffix="%" />
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <AlertTriangle className="h-4 w-4" />
              风险等级
            </div>
            <Badge className="mt-3">{riskLabel(metrics.riskLevel)}</Badge>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-lg">关键指标</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <ProgressRow label="任务推进" value={metrics.taskProgress} />
          <ProgressRow label="质量表现" value={metrics.qualityScore} />
          <ProgressRow label="团队利用率" value={metrics.teamEfficiency} />
          <ProgressRow label="项目健康度" value={metrics.healthScore} />
        </CardContent>
      </Card>
    </div>
  );
};

const riskLabel = (level: string) => ({ LOW: '低', MEDIUM: '中', HIGH: '高', CRITICAL: '严重' }[level] ?? level);

const MetricCard: React.FC<{ icon: React.ReactNode; label: string; value: number; suffix?: string }> = ({ icon, label, value, suffix = '' }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">{icon}{label}</div>
      <div className="mt-2 text-2xl font-semibold">{Math.round(value)}{suffix}</div>
    </CardContent>
  </Card>
);

const ProgressRow: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="space-y-2">
    <div className="flex justify-between text-sm"><span>{label}</span><span>{Math.round(value)}%</span></div>
    <Progress value={value} />
  </div>
);

export default PerformanceAnalysis;
