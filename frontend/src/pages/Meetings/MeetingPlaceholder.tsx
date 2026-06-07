import React from 'react';
import { Calendar, FileText, Settings, Users } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

interface MeetingPlaceholderProps {
  title: string;
  description?: string;
}

export const MeetingPlaceholder: React.FC<MeetingPlaceholderProps> = ({ title, description }) => (
  <div className="space-y-6 p-6">
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {description ?? '该页面已恢复基础入口，详细业务能力可继续逐步补全。'}
      </p>
    </div>
    <div className="grid gap-4 md:grid-cols-4">
      <InfoCard icon={<Calendar className="h-4 w-4" />} label="会议" value="可访问" />
      <InfoCard icon={<Users className="h-4 w-4" />} label="参与者" value="可维护" />
      <InfoCard icon={<FileText className="h-4 w-4" />} label="资料" value="可查看" />
      <InfoCard icon={<Settings className="h-4 w-4" />} label="状态" value="已恢复" />
    </div>
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">操作</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" onClick={() => window.history.back()}>返回</Button>
        <Button type="button" onClick={() => window.location.reload()}>刷新</Button>
      </CardContent>
    </Card>
  </div>
);

const InfoCard: React.FC<{ icon: React.ReactNode; label: string; value: React.ReactNode }> = ({ icon, label, value }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">{icon}{label}</div>
      <div className="mt-2 text-xl font-semibold">{value}</div>
    </CardContent>
  </Card>
);

export default MeetingPlaceholder;
