import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Link, Loader2, RefreshCw, TrendingUp } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Progress } from '@/components/ui/Progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Textarea } from '@/components/ui/Textarea';
import { useProjectMeetings } from '@/hooks/meeting/useProjectMeetings';

interface MeetingTaskManagerProps {
  projectId: number;
  meetingId: number;
  onTasksUpdated?: () => void;
}

const statusLabels: Record<string, string> = {
  TODO: '待办',
  IN_PROGRESS: '进行中',
  TESTING: '测试中',
  COMPLETED: '已完成',
  BLOCKED: '阻塞',
};

const priorityLabels: Record<string, string> = {
  LOW: '低',
  MEDIUM: '中',
  HIGH: '高',
  URGENT: '紧急',
};

export const MeetingTaskManager: React.FC<MeetingTaskManagerProps> = ({
  projectId,
  meetingId,
  onTasksUpdated,
}) => {
  const {
    getMeetingRelatedTasks,
    syncMeetingTasksWithProject,
    linkExistingTaskToMeeting,
    getMeetingTaskProgressSummary,
    updateTasksFromMeetingProgress,
    loading,
  } = useProjectMeetings(projectId);

  const [tasks, setTasks] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [updateOpen, setUpdateOpen] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);
  const [linkTaskId, setLinkTaskId] = useState('');
  const [status, setStatus] = useState('IN_PROGRESS');
  const [actualHours, setActualHours] = useState('');
  const [notes, setNotes] = useState('');

  const loadData = async () => {
    try {
      setError(null);
      const [taskResult, summaryResult] = await Promise.all([
        getMeetingRelatedTasks(meetingId),
        getMeetingTaskProgressSummary(meetingId),
      ]);
      setTasks(taskResult?.tasks ?? []);
      setSummary(summaryResult);
    } catch (err) {
      console.error('Failed to load meeting tasks:', err);
      setError('加载会议任务失败');
    }
  };

  useEffect(() => {
    void loadData();
  }, [meetingId, projectId]);

  const handleSync = async () => {
    await syncMeetingTasksWithProject(meetingId);
    await loadData();
    onTasksUpdated?.();
  };

  const handleLink = async () => {
    const taskId = Number(linkTaskId);
    if (!taskId) {
      setError('请输入有效的任务 ID');
      return;
    }
    await linkExistingTaskToMeeting(meetingId, taskId);
    setLinkOpen(false);
    setLinkTaskId('');
    await loadData();
    onTasksUpdated?.();
  };

  const handleUpdate = async () => {
    if (!selectedTask) return;
    await updateTasksFromMeetingProgress(meetingId, [{
      task_id: selectedTask.id,
      status,
      actual_hours: actualHours ? Number(actualHours) : undefined,
      progress_notes: notes || undefined,
    }]);
    setUpdateOpen(false);
    setSelectedTask(null);
    await loadData();
    onTasksUpdated?.();
  };

  const openUpdate = (task: any) => {
    setSelectedTask(task);
    setStatus(task.status ?? 'IN_PROGRESS');
    setActualHours('');
    setNotes('');
    setUpdateOpen(true);
  };

  const completed = summary?.completed_tasks ?? tasks.filter((task) => task.status === 'COMPLETED').length;
  const total = summary?.total_tasks ?? tasks.length;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="space-y-4">
      {error && (
        <Alert className="border-red-200 bg-red-50 text-red-700">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">任务总数</div>
            <div className="mt-1 text-2xl font-semibold">{total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">已完成</div>
            <div className="mt-1 text-2xl font-semibold">{completed}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-2 pt-6">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">完成进度</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <TrendingUp className="h-5 w-5" />
            会议关联任务
          </CardTitle>
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => setLinkOpen(true)}>
              <Link className="mr-2 h-4 w-4" />
              关联任务
            </Button>
            <Button type="button" onClick={handleSync} disabled={loading}>
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
              同步任务
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>任务</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>优先级</TableHead>
                <TableHead>负责人</TableHead>
                <TableHead>截止时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell>
                    <div className="font-medium">{task.title || task.name || `任务 #${task.id}`}</div>
                    {task.description && <div className="text-xs text-muted-foreground">{task.description}</div>}
                  </TableCell>
                  <TableCell><Badge variant="outline">{statusLabels[task.status] ?? task.status ?? '-'}</Badge></TableCell>
                  <TableCell>{priorityLabels[task.priority] ?? task.priority ?? '-'}</TableCell>
                  <TableCell>{task.assignee_name ?? task.assignee?.name ?? '-'}</TableCell>
                  <TableCell>{task.due_date ? new Date(task.due_date).toLocaleDateString('zh-CN') : '-'}</TableCell>
                  <TableCell className="text-right">
                    <Button type="button" variant="outline" size="sm" onClick={() => openUpdate(task)}>
                      更新进度
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {tasks.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                    暂无关联任务
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={linkOpen} onOpenChange={setLinkOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>关联已有任务</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>任务 ID</Label>
              <Input value={linkTaskId} onChange={(event) => setLinkTaskId(event.target.value)} type="number" />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setLinkOpen(false)}>取消</Button>
              <Button type="button" onClick={handleLink}>关联</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={updateOpen} onOpenChange={setUpdateOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>更新任务进度</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>状态</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(statusLabels).map(([value, label]) => (
                    <SelectItem key={value} value={value}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>实际工时</Label>
              <Input type="number" min="0" step="0.5" value={actualHours} onChange={(event) => setActualHours(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>进度说明</Label>
              <Textarea value={notes} onChange={(event) => setNotes(event.target.value)} />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setUpdateOpen(false)}>取消</Button>
              <Button type="button" onClick={handleUpdate}>
                <CheckCircle className="mr-2 h-4 w-4" />
                保存
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
