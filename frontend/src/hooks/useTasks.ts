// @ts-nocheck
import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { TaskService, type CreateTaskRequest, type TaskFilters, type UpdateTaskRequest } from '@/services/taskService';
import { useToast } from '@/hooks/useToast';
import type { Task } from '@/types/project';

const getErrorMessage = (error: any, fallback: string) =>
  error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback;

const invalidateTaskQueries = (queryClient: ReturnType<typeof useQueryClient>, task?: Task) => {
  queryClient.invalidateQueries({ queryKey: ['tasks'] });
  if (task?.id) queryClient.invalidateQueries({ queryKey: ['task', task.id] });
  if (task?.project_id) queryClient.invalidateQueries({ queryKey: ['projects', task.project_id] });
};

export function useTasks(filters?: TaskFilters) {
  return useQuery({
    queryKey: ['tasks', filters],
    queryFn: () => TaskService.getTasks(filters),
    staleTime: 30000
  });
}

export function useTask(id: number) {
  return useQuery({
    queryKey: ['task', id],
    queryFn: () => TaskService.getTask(id),
    enabled: Boolean(id)
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: CreateTaskRequest) => TaskService.createTask(data),
    onSuccess: (task) => {
      invalidateTaskQueries(queryClient, task);
      toast({
        title: '任务创建成功',
        description: `任务「${task.task_name}」已创建`
      });
    },
    onError: (error: any) => {
      toast({
        title: '任务创建失败',
        description: getErrorMessage(error, '请稍后重试'),
        variant: 'destructive'
      });
    }
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateTaskRequest }) => TaskService.updateTask(id, data),
    onSuccess: (task) => {
      invalidateTaskQueries(queryClient, task);
      toast({
        title: '任务更新成功',
        description: `任务「${task.task_name}」已更新`
      });
    },
    onError: (error: any) => {
      toast({
        title: '任务更新失败',
        description: getErrorMessage(error, '请稍后重试'),
        variant: 'destructive'
      });
    }
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (id: number) => TaskService.deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast({
        title: '任务删除成功',
        description: '任务已删除'
      });
    },
    onError: (error: any) => {
      toast({
        title: '任务删除失败',
        description: getErrorMessage(error, '请稍后重试'),
        variant: 'destructive'
      });
    }
  });
}

export function useUpdateTaskStatus() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, status, reason }: { id: number; status: Task['status']; reason?: string }) =>
      TaskService.updateTaskStatus(id, { status, reason }),
    onSuccess: (task) => {
      invalidateTaskQueries(queryClient, task);
      toast({
        title: '任务状态更新成功',
        description: `任务状态已更新为「${getStatusLabel(task.status)}」`
      });
    },
    onError: (error: any) => {
      toast({
        title: '任务状态更新失败',
        description: getErrorMessage(error, '请稍后重试'),
        variant: 'destructive'
      });
    }
  });
}

export function useAssignTask() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, assignee_id, reason }: { id: number; assignee_id: number; reason?: string }) =>
      TaskService.assignTask(id, { assignee_id, reason }),
    onSuccess: (task) => {
      invalidateTaskQueries(queryClient, task);
      toast({
        title: '任务分配成功',
        description: `任务已分配给 ${task.assignee?.full_name || task.assignee?.username || '指定用户'}`
      });
    },
    onError: (error: any) => {
      toast({
        title: '任务分配失败',
        description: getErrorMessage(error, '请稍后重试'),
        variant: 'destructive'
      });
    }
  });
}

export function useUpdateTaskProgress() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({
      id,
      data
    }: {
      id: number;
      data: { actual_hours?: number; remaining_hours?: number; progress_notes?: string; issues_encountered?: string };
    }) => TaskService.updateTaskProgress(id, data),
    onSuccess: (task) => {
      invalidateTaskQueries(queryClient, task);
      toast({
        title: '任务进度更新成功',
        description: '任务进度已更新'
      });
    },
    onError: (error: any) => {
      toast({
        title: '任务进度更新失败',
        description: getErrorMessage(error, '请稍后重试'),
        variant: 'destructive'
      });
    }
  });
}

export function useTaskStatistics(projectId: number) {
  return useQuery({
    queryKey: ['task-statistics', projectId],
    queryFn: () => TaskService.getTaskStatistics(projectId),
    enabled: Boolean(projectId),
    staleTime: 60000
  });
}

export function useTaskDependencies(taskId: number) {
  return useQuery({
    queryKey: ['task-dependencies', taskId],
    queryFn: () => TaskService.getTaskDependencies(taskId),
    enabled: Boolean(taskId)
  });
}

export function useSetTaskDependencies() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, dependency_tasks }: { id: number; dependency_tasks: number[] }) =>
      TaskService.setTaskDependencies(id, { dependency_tasks }),
    onSuccess: (task) => {
      invalidateTaskQueries(queryClient, task);
      queryClient.invalidateQueries({ queryKey: ['task-dependencies', task.id] });
      toast({
        title: '任务依赖设置成功',
        description: '任务依赖关系已更新'
      });
    },
    onError: (error: any) => {
      toast({
        title: '任务依赖设置失败',
        description: getErrorMessage(error, '请稍后重试'),
        variant: 'destructive'
      });
    }
  });
}

export function useProjectCriticalPath(projectId: number) {
  return useQuery({
    queryKey: ['critical-path', projectId],
    queryFn: () => TaskService.getProjectCriticalPath(projectId),
    enabled: Boolean(projectId),
    staleTime: 300000
  });
}

export function getStatusLabel(status: Task['status']): string {
  const statusLabels: Record<Task['status'], string> = {
    TODO: '待开始',
    ASSIGNED: '已分配',
    IN_PROGRESS: '进行中',
    ON_HOLD: '暂停',
    BLOCKED: '阻塞',
    PENDING_REVIEW: '待审核',
    COMPLETED: '已完成',
    CANCELLED: '已取消'
  };
  return statusLabels[status] || status;
}

export function getStatusColor(status: Task['status']): string {
  const statusColors: Record<Task['status'], string> = {
    TODO: 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800',
    ASSIGNED: 'bg-blue-100 text-blue-800 dark:text-blue-300 dark:bg-blue-900/30',
    IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
    ON_HOLD: 'bg-orange-100 text-orange-800 dark:text-orange-300 dark:bg-orange-900/30',
    BLOCKED: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30',
    PENDING_REVIEW: 'bg-purple-100 text-purple-800 dark:text-purple-300 dark:bg-purple-900/30',
    COMPLETED: 'bg-green-100 text-green-800',
    CANCELLED: 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800'
  };
  return statusColors[status] || 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800';
}

export function getPriorityLabel(priority: Task['priority']): string {
  const priorityLabels: Record<Task['priority'], string> = {
    LOW: '低',
    MEDIUM: '中',
    HIGH: '高',
    URGENT: '紧急'
  };
  return priorityLabels[priority] || priority;
}

export function getPriorityColor(priority: Task['priority']): string {
  const priorityColors: Record<Task['priority'], string> = {
    LOW: 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800',
    MEDIUM: 'bg-blue-100 text-blue-800 dark:text-blue-300 dark:bg-blue-900/30',
    HIGH: 'bg-orange-100 text-orange-800 dark:text-orange-300 dark:bg-orange-900/30',
    URGENT: 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30'
  };
  return priorityColors[priority] || 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800';
}

export function getTaskTypeLabel(type: Task['task_type']): string {
  const typeLabels: Record<Task['task_type'], string> = {
    REQUIREMENT_ANALYSIS: '需求分析',
    TEST_DESIGN: '测试设计',
    TEST_EXECUTION: '测试执行',
    AUTOMATION_DEVELOPMENT: '自动化开发',
    PERFORMANCE_TEST: '性能测试',
    SECURITY_TEST: '安全测试',
    ENVIRONMENT_SETUP: '环境搭建',
    DOCUMENTATION: '文档编写'
  };
  return typeLabels[type] || type;
}

export function useTaskBoard(projectId?: number) {
  const [filters, setFilters] = useState<TaskFilters>({
    project_id: projectId,
    page: 1,
    size: 100
  });

  const { data: tasksData, isLoading, error, refetch } = useTasks(filters);

  const updateFilters = useCallback((newFilters: Partial<TaskFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  }, []);

  const groupTasksByStatus = useCallback((tasks: Task[]) => {
    const groups: Record<Task['status'], Task[]> = {
      TODO: [],
      ASSIGNED: [],
      IN_PROGRESS: [],
      ON_HOLD: [],
      BLOCKED: [],
      PENDING_REVIEW: [],
      COMPLETED: [],
      CANCELLED: []
    };

    tasks.forEach((task) => {
      if (groups[task.status]) groups[task.status].push(task);
    });

    return groups;
  }, []);

  const tasks = tasksData?.items || tasksData?.data || [];
  const taskGroups = tasks.length ? groupTasksByStatus(tasks) : null;

  return {
    tasks,
    taskGroups,
    total: tasksData?.total || tasks.length,
    isLoading,
    error,
    filters,
    updateFilters,
    refetch
  };
}
