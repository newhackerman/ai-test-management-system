import React, { useEffect, useState } from 'react';
import { Award, Target, TrendingUp, Users } from 'lucide-react';

import { Badge } from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import { cn } from '@/lib/utils';

interface TeamPerformanceDashboardProps {
  projectId: number;
  className?: string;
}

interface TeamMember {
  userId: number;
  userName: string;
  role: string;
  tasksCompleted: number;
  hoursWorked: number;
  efficiency: number;
  qualityScore: number;
  collaborationScore: number;
  overallScore: number;
}

export const TeamPerformanceDashboard: React.FC<TeamPerformanceDashboardProps> = ({ projectId, className }) => {
  const [members, setMembers] = useState<TeamMember[]>([]);

  useEffect(() => {
    fetch(`/api/v1/project-statistics/projects/${projectId}/performance/team`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('load failed')))
      .then((data) => {
        const rows = Array.isArray(data) ? data : data.members;
        if (Array.isArray(rows)) {
          setMembers(rows.map((item: any) => ({
            userId: item.userId ?? item.user_id,
            userName: item.userName ?? item.user_name ?? item.username ?? '成员',
            role: item.role ?? '成员',
            tasksCompleted: Number(item.tasksCompleted ?? item.tasks_completed ?? 0),
            hoursWorked: Number(item.hoursWorked ?? item.hours_worked ?? 0),
            efficiency: Number(item.efficiency ?? 0),
            qualityScore: Number(item.qualityScore ?? item.quality_score ?? 0),
            collaborationScore: Number(item.collaborationScore ?? item.collaboration_score ?? 0),
            overallScore: Number(item.overallScore ?? item.overall_score ?? 0),
          })));
        }
      })
      .catch(() => undefined);
  }, [projectId]);

  const avg = (field: keyof Pick<TeamMember, 'efficiency' | 'qualityScore' | 'collaborationScore' | 'overallScore'>) =>
    members.reduce((sum, item) => sum + item[field], 0) / Math.max(members.length, 1);

  return (
    <div className={cn('space-y-4', className)}>
      <div className="grid gap-4 md:grid-cols-4">
        <Summary icon={<Users className="h-4 w-4" />} label="成员数" value={members.length} />
        <Summary icon={<TrendingUp className="h-4 w-4" />} label="平均效率" value={`${Math.round(avg('efficiency'))}%`} />
        <Summary icon={<Target className="h-4 w-4" />} label="质量得分" value={`${Math.round(avg('qualityScore'))}%`} />
        <Summary icon={<Award className="h-4 w-4" />} label="综合得分" value={`${Math.round(avg('overallScore'))}%`} />
      </div>
      <Card>
        <CardHeader><CardTitle className="text-lg">团队绩效</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {members.map((member) => (
            <div key={member.userId} className="rounded-md border p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="font-medium">{member.userName}</div>
                  <div className="text-xs text-muted-foreground">{member.role} · 完成 {member.tasksCompleted} 个任务 · {member.hoursWorked} 小时</div>
                </div>
                <Badge>{Math.round(member.overallScore)} 分</Badge>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <ProgressItem label="效率" value={member.efficiency} />
                <ProgressItem label="质量" value={member.qualityScore} />
                <ProgressItem label="协作" value={member.collaborationScore} />
              </div>
            </div>
          ))}
          {members.length === 0 && <div className="flex h-32 items-center justify-center text-muted-foreground">暂无团队绩效数据</div>}
        </CardContent>
      </Card>
    </div>
  );
};

const Summary: React.FC<{ icon: React.ReactNode; label: string; value: React.ReactNode }> = ({ icon, label, value }) => (
  <Card><CardContent className="pt-6"><div className="flex items-center gap-2 text-sm text-muted-foreground">{icon}{label}</div><div className="mt-2 text-2xl font-semibold">{value}</div></CardContent></Card>
);

const ProgressItem: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="space-y-1"><div className="flex justify-between text-xs"><span>{label}</span><span>{Math.round(value)}%</span></div><Progress value={value} /></div>
);

export default TeamPerformanceDashboard;
