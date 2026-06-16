// @ts-nocheck
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Calendar, CheckCircle2, Clock, Loader2, Plus, RefreshCw, Users } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Switch } from '@/components/ui/Switch';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Textarea } from '@/components/ui/Textarea';
import { useProjectMeetings } from '@/hooks/meeting/useProjectMeetings';
import { Meeting, MeetingStatus, MeetingType } from '@/types/meeting';

interface ProjectMeetingManagerProps {
  projectId?: number;
}

const meetingTypeLabels: Record<string, string> = {
  PROJECT_KICKOFF: '项目启动会',
  REQUIREMENT_REVIEW: '需求评审会',
  DESIGN_REVIEW: '设计评审会',
  CODE_REVIEW: '代码评审会',
  TEST_REVIEW: '测试评审会',
  PROGRESS_SYNC: '进度同步会',
  PROBLEM_SOLVING: '问题解决会',
  PROJECT_SUMMARY: '项目总结会',
  TRAINING: '培训',
  OTHER: '其他'
};

const statusLabels: Record<string, string> = {
  SCHEDULED: '已安排',
  IN_PROGRESS: '进行中',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  POSTPONED: '已延期'
};

const formatDateTime = (value?: string) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

const createInitialForm = () => ({
  title: '',
  description: '',
  meeting_type: MeetingType.PROGRESS_SYNC,
  scheduled_start_time: '',
  scheduled_end_time: '',
  max_participants: '100',
  is_recording_enabled: false,
  is_waiting_room_enabled: true,
  auto_invite_team: true
});

export const ProjectMeetingManager: React.FC<ProjectMeetingManagerProps> = ({ projectId: propProjectId }) => {
  const { projectId: routeProjectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const projectId = propProjectId ?? Number(routeProjectId ?? 0);

  const {
    meetings,
    loading,
    error,
    totalCount,
    createProjectMeeting,
    syncTeamToMeeting,
    generateMeetingSchedule,
    getMeetingStatistics,
    refreshMeetings
  } = useProjectMeetings(projectId);

  const [activeTab, setActiveTab] = useState('meetings');
  const [createOpen, setCreateOpen] = useState(false);
  const [schedule, setSchedule] = useState<any[]>([]);
  const [statistics, setStatistics] = useState<any>(null);
  const [form, setForm] = useState(createInitialForm);

  const safeMeetings = Array.isArray(meetings) ? meetings : [];
  const meetingCount = totalCount || safeMeetings.length;

  const statusSummary = useMemo(
    () => ({
      completed: safeMeetings.filter((meeting) => meeting.status === MeetingStatus.COMPLETED).length,
      inProgress: safeMeetings.filter((meeting) => meeting.status === MeetingStatus.IN_PROGRESS).length
    }),
    [safeMeetings]
  );

  useEffect(() => {
    if (!projectId) return;

    if (activeTab === 'statistics') {
      getMeetingStatistics().then(setStatistics).catch(console.error);
    }

    if (activeTab === 'schedule') {
      generateMeetingSchedule({ weekly_sync: true, milestone_reviews: true, task_reviews: true })
        .then((result: any) => setSchedule(Array.isArray(result?.schedule) ? result.schedule : Array.isArray(result) ? result : []))
        .catch(console.error);
    }
  }, [activeTab, generateMeetingSchedule, getMeetingStatistics, projectId]);

  const updateForm = (field: keyof ReturnType<typeof createInitialForm>, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const createMeeting = async () => {
    if (!projectId || !form.title.trim() || !form.scheduled_start_time || !form.scheduled_end_time) return;

    await createProjectMeeting({
      title: form.title.trim(),
      description: form.description || undefined,
      meeting_type: form.meeting_type,
      scheduled_start_time: new Date(form.scheduled_start_time).toISOString(),
      scheduled_end_time: new Date(form.scheduled_end_time).toISOString(),
      max_participants: Number(form.max_participants) || 100,
      is_recording_enabled: form.is_recording_enabled,
      is_waiting_room_enabled: form.is_waiting_room_enabled,
      participants: [],
      project_id: projectId,
      meeting_settings: {
        auto_record: form.is_recording_enabled,
        waiting_room_enabled: form.is_waiting_room_enabled
      }
    });

    setCreateOpen(false);
    setForm(createInitialForm());
    await refreshMeetings();
  };

  const syncTeam = async (meeting: Meeting) => {
    await syncTeamToMeeting(meeting.id);
    await refreshMeetings();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">项目会议</h1>
          <p className="text-sm text-muted-foreground">项目 #{projectId || '-'} 的会议安排、同步和统计</p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={() => refreshMeetings()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button type="button" onClick={() => setCreateOpen(true)} disabled={!projectId}>
            <Plus className="mr-2 h-4 w-4" />
            新建会议
          </Button>
        </div>
      </div>

      {error && (
        <Alert className="border-red-200 bg-red-50 text-red-700 dark:text-red-400 dark:bg-red-900/20 dark:border-red-800">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="meetings">会议列表</TabsTrigger>
          <TabsTrigger value="schedule">会议计划</TabsTrigger>
          <TabsTrigger value="statistics">统计</TabsTrigger>
        </TabsList>

        <TabsContent value="meetings">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">会议列表（{meetingCount}）</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex h-40 items-center justify-center text-muted-foreground">
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  加载中...
                </div>
              ) : (
                <MeetingTable
                  meetings={safeMeetings}
                  onOpen={(meeting) => navigate(`/meetings/${meeting.id}`)}
                  onSyncTeam={syncTeam}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="schedule">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">推荐会议计划</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>标题</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>日期</TableHead>
                    <TableHead>时长</TableHead>
                    <TableHead>优先级</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {schedule.map((item, index) => (
                    <TableRow key={`${item.title || 'schedule'}-${index}`}>
                      <TableCell>{item.title || '-'}</TableCell>
                      <TableCell>{meetingTypeLabels[item.type] ?? item.type ?? '-'}</TableCell>
                      <TableCell>{item.scheduled_date ? new Date(item.scheduled_date).toLocaleDateString('zh-CN') : '-'}</TableCell>
                      <TableCell>{item.duration ?? '-'} 分钟</TableCell>
                      <TableCell>{item.priority ?? '-'}</TableCell>
                    </TableRow>
                  ))}
                  {schedule.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                        暂无计划
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="statistics">
          <div className="grid gap-4 md:grid-cols-4">
            <StatCard icon={<Calendar className="h-4 w-4" />} label="会议总数" value={statistics?.total_meetings ?? meetingCount} />
            <StatCard icon={<CheckCircle2 className="h-4 w-4" />} label="已完成" value={statistics?.completed_meetings ?? statusSummary.completed} />
            <StatCard icon={<Clock className="h-4 w-4" />} label="平均时长" value={`${statistics?.avg_duration_minutes ?? 0} 分钟`} />
            <StatCard icon={<Users className="h-4 w-4" />} label="进行中" value={statistics?.in_progress_meetings ?? statusSummary.inProgress} />
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>新建项目会议</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2 md:col-span-2">
              <Label>标题</Label>
              <Input value={form.title} onChange={(event) => updateForm('title', event.target.value)} />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>描述</Label>
              <Textarea value={form.description} onChange={(event) => updateForm('description', event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>类型</Label>
              <select
                className="h-10 w-full rounded-md border px-3 text-sm"
                value={form.meeting_type}
                onChange={(event) => updateForm('meeting_type', event.target.value)}
              >
                {Object.values(MeetingType).map((type) => (
                  <option key={type} value={type}>
                    {meetingTypeLabels[type] ?? type}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>人数上限</Label>
              <Input
                type="number"
                min="1"
                value={form.max_participants}
                onChange={(event) => updateForm('max_participants', event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>开始时间</Label>
              <Input
                type="datetime-local"
                value={form.scheduled_start_time}
                onChange={(event) => updateForm('scheduled_start_time', event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>结束时间</Label>
              <Input
                type="datetime-local"
                value={form.scheduled_end_time}
                onChange={(event) => updateForm('scheduled_end_time', event.target.value)}
              />
            </div>
            <Switch
              checked={form.is_recording_enabled}
              onCheckedChange={(checked) => updateForm('is_recording_enabled', checked)}
              label="开启录制"
            />
            <Switch
              checked={form.is_waiting_room_enabled}
              onCheckedChange={(checked) => updateForm('is_waiting_room_enabled', checked)}
              label="启用等候室"
            />
            <Switch
              checked={form.auto_invite_team}
              onCheckedChange={(checked) => updateForm('auto_invite_team', checked)}
              label="自动邀请项目成员"
            />
          </div>
          <div className="mt-6 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
              取消
            </Button>
            <Button type="button" onClick={createMeeting} disabled={loading || !form.title.trim()}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              创建
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const MeetingTable: React.FC<{
  meetings: Meeting[];
  onOpen: (meeting: Meeting) => void;
  onSyncTeam: (meeting: Meeting) => void;
}> = ({ meetings, onOpen, onSyncTeam }) => (
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead>标题</TableHead>
        <TableHead>类型</TableHead>
        <TableHead>状态</TableHead>
        <TableHead>时间</TableHead>
        <TableHead>人数</TableHead>
        <TableHead className="text-right">操作</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {meetings.map((meeting) => (
        <TableRow key={meeting.id}>
          <TableCell className="font-medium">{meeting.title}</TableCell>
          <TableCell>{meetingTypeLabels[meeting.meeting_type] ?? meeting.meeting_type}</TableCell>
          <TableCell>
            <Badge variant="outline">{statusLabels[meeting.status] ?? meeting.status}</Badge>
          </TableCell>
          <TableCell>{formatDateTime(meeting.scheduled_start_time)}</TableCell>
          <TableCell>
            {meeting.participant_count ?? 0}/{meeting.max_participants ?? '-'}
          </TableCell>
          <TableCell className="text-right">
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => onSyncTeam(meeting)}>
                同步成员
              </Button>
              <Button type="button" size="sm" onClick={() => onOpen(meeting)}>
                查看
              </Button>
            </div>
          </TableCell>
        </TableRow>
      ))}
      {meetings.length === 0 && (
        <TableRow>
          <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
            暂无会议
          </TableCell>
        </TableRow>
      )}
    </TableBody>
  </Table>
);

const StatCard: React.FC<{ icon: React.ReactNode; label: string; value: React.ReactNode }> = ({ icon, label, value }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </CardContent>
  </Card>
);

export default ProjectMeetingManager;
