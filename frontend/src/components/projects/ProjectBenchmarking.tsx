import React, { useEffect, useState } from 'react';
import { Award, BarChart3, Target, TrendingUp } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import { cn } from '@/lib/utils';

interface ProjectBenchmarkingProps {
  projectId: number;
  className?: string;
}

interface BenchmarkMetric {
  name: string;
  current: number;
  average: number;
  top: number;
}

export const ProjectBenchmarking: React.FC<ProjectBenchmarkingProps> = ({ projectId, className }) => {
  const [metrics, setMetrics] = useState<BenchmarkMetric[]>([
    { name: '整体得分', current: 0, average: 70, top: 90 },
    { name: '进度表现', current: 0, average: 68, top: 92 },
    { name: '质量得分', current: 0, average: 75, top: 94 },
    { name: '团队效率', current: 0, average: 72, top: 91 },
  ]);

  useEffect(() => {
    fetch(`/api/v1/project-statistics/projects/${projectId}/benchmarking`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('load failed')))
      .then((data) => {
        const next = data.metrics ?? data.benchmarks;
        if (Array.isArray(next)) setMetrics(next);
      })
      .catch(() => undefined);
  }, [projectId]);

  const overall = Math.round(metrics.reduce((sum, item) => sum + item.current, 0) / Math.max(metrics.length, 1));

  return (
    <div className={cn('space-y-4', className)}>
      <div className="grid gap-4 md:grid-cols-3">
        <Summary icon={<Award className="h-4 w-4" />} label="综合得分" value={overall} />
        <Summary icon={<TrendingUp className="h-4 w-4" />} label="行业均值" value={Math.round(avg(metrics, 'average'))} />
        <Summary icon={<Target className="h-4 w-4" />} label="优秀水平" value={Math.round(avg(metrics, 'top'))} />
      </div>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><BarChart3 className="h-5 w-5" />项目对标</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {metrics.map((metric) => (
            <div key={metric.name} className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>{metric.name}</span>
                <span>当前 {metric.current} / 均值 {metric.average} / 优秀 {metric.top}</span>
              </div>
              <Progress value={metric.current} />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};

const avg = (items: BenchmarkMetric[], key: keyof Pick<BenchmarkMetric, 'average' | 'top'>) =>
  items.reduce((sum, item) => sum + item[key], 0) / Math.max(items.length, 1);

const Summary: React.FC<{ icon: React.ReactNode; label: string; value: number }> = ({ icon, label, value }) => (
  <Card><CardContent className="pt-6"><div className="flex items-center gap-2 text-sm text-muted-foreground">{icon}{label}</div><div className="mt-2 text-2xl font-semibold">{value}</div></CardContent></Card>
);

export default ProjectBenchmarking;
