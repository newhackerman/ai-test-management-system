import React, { useEffect, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle, Clock, Target, Users } from 'lucide-react';

import { Badge } from '../ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Progress } from '../ui/Progress';

interface StatisticsDashboardProps {
  projectId: number;
  className?: string;
}

interface ProjectStatistics {
  overall_progress?: number;
  task_progress?: { total_tasks?: number; completed_tasks?: number; progress_rate?: number; overdue_tasks?: number };
  quality_progress?: { quality_score?: number; defect_count?: number; test_pass_rate?: number };
  collaboration_metrics?: { team_size?: number; collaboration_score?: number };
  risk_metrics?: { total_risks?: number; high_risks?: number };
}

const StatisticsDashboard: React.FC<StatisticsDashboardProps> = ({ projectId, className = '' }) => {
  const [stats, setStats] = useState<ProjectStatistics | null>(null);

  useEffect(() => {
    fetch(`/api/v1/project-statistics/projects/${projectId}`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('load failed')))
      .then(setStats)
      .catch(() => setStats(null));
  }, [projectId]);

  const taskProgress = stats?.task_progress?.progress_rate ?? stats?.overall_progress ?? 0;
  const quality = stats?.quality_progress?.quality_score ?? 0;
  const collaboration = stats?.collaboration_metrics?.collaboration_score ?? 0;

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Stat icon={<Activity className="h-4 w-4" />} label="整体进度" value={`${Math.round(stats?.overall_progress ?? 0)}%`} />
        <Stat icon={<Target className="h-4 w-4" />} label="任务" value={`${stats?.task_progress?.completed_tasks ?? 0}/${stats?.task_progress?.total_tasks ?? 0}`} />
        <Stat icon={<CheckCircle className="h-4 w-4" />} label="质量得分" value={`${Math.round(quality)}%`} />
        <Stat icon={<Users className="h-4 w-4" />} label="团队规模" value={stats?.collaboration_metrics?.team_size ?? 0} />
      </div>
      <Card>
        <CardHeader><CardTitle className="text-lg">项目统计概览</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <ProgressItem label="任务进度" value={taskProgress} />
          <ProgressItem label="测试通过率" value={stats?.quality_progress?.test_pass_rate ?? 0} />
          <ProgressItem label="质量得分" value={quality} />
          <ProgressItem label="协作得分" value={collaboration} />
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-orange-600 dark:text-orange-400" />
            <span className="text-sm">高风险 {stats?.risk_metrics?.high_risks ?? 0} / 总风险 {stats?.risk_metrics?.total_risks ?? 0}</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <Badge variant="outline">实时统计</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const Stat: React.FC<{ icon: React.ReactNode; label: string; value: React.ReactNode }> = ({ icon, label, value }) => (
  <Card><CardContent className="pt-6"><div className="flex items-center gap-2 text-sm text-muted-foreground">{icon}{label}</div><div className="mt-2 text-2xl font-semibold">{value}</div></CardContent></Card>
);

const ProgressItem: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="space-y-2"><div className="flex justify-between text-sm"><span>{label}</span><span>{Math.round(value)}%</span></div><Progress value={value} /></div>
);

export default StatisticsDashboard;
