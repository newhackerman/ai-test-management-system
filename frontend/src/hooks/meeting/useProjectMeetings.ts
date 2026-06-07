// @ts-nocheck
/**
 * 椤圭洰浼氳绠＄悊Hook
 * 
 * 鎻愪緵椤圭洰鐩稿叧鐨勪細璁鐞嗗姛鑳斤紝鍖呮嫭锛?
 * - 鑾峰彇椤圭洰浼氳鍒楄〃
 * - 鍒涘缓椤圭洰浼氳
 * - 鍚屾椤圭洰鍥㈤槦鎴愬憳
 * - 鐢熸垚浼氳璁″垝
 * - 鑾峰彇浼氳缁熻
 */
import { useState, useEffect, useCallback } from 'react';
import { projectMeetingService } from '@/services/meeting/projectMeetingService';
import { Meeting, CreateProjectMeetingRequest } from '@/types/meeting';
import { useToast } from '@/hooks/useToast';

interface UseProjectMeetingsOptions {
  autoLoad?: boolean;
  meetingType?: string;
  status?: string;
  dateRange?: {
    start?: Date;
    end?: Date;
  };
}

interface MeetingScheduleConfig {
  weekly_sync?: boolean;
  milestone_reviews?: boolean;
  task_reviews?: boolean;
  auto_create_kickoff?: boolean;
}

interface MeetingDecision {
  title: string;
  description?: string;
  create_task: boolean;
  task_type?: string;
  priority?: string;
  assignee_id?: number;
  start_date?: Date;
  due_date?: Date;
  estimated_hours?: number;
  acceptance_criteria?: string;
}

export const useProjectMeetings = (
  projectId: number,
  options: UseProjectMeetingsOptions = {}
) => {
  const { toast } = useToast();
  
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [projectInfo, setProjectInfo] = useState<any>(null);

  // 鑾峰彇椤圭洰浼氳鍒楄〃
  const fetchMeetings = useCallback(async (
    meetingType?: string,
    status?: string,
    dateRange?: { start?: Date; end?: Date }
  ) => {
    if (!projectId) return;

    try {
      setLoading(true);
      setError(null);

      const response = await projectMeetingService.getProjectMeetings(
        projectId,
        {
          meeting_type: meetingType,
          status,
          start_date: dateRange?.start,
          end_date: dateRange?.end,
        }
      );

      setMeetings(response.meetings);
      setTotalCount(response.total_count);
      setProjectInfo(response.project_info);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鑾峰彇浼氳鍒楄〃澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [projectId, toast]);

  // 鍒涘缓椤圭洰浼氳
  const createProjectMeeting = useCallback(async (
    meetingData: CreateProjectMeetingRequest
  ): Promise<Meeting> => {
    try {
      setLoading(true);
      
      const meeting = await projectMeetingService.createProjectMeeting(
        projectId,
        meetingData
      );

      // 鍒锋柊浼氳鍒楄〃
      await fetchMeetings(
        options.meetingType,
        options.status,
        options.dateRange
      );

      toast({
        title: '鎴愬姛',
        description: '浼氳鍒涘缓鎴愬姛',
        variant: 'default',
      });

      return meeting;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鍒涘缓浼氳澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, fetchMeetings, options, toast]);

  // 鍚屾椤圭洰鍥㈤槦鎴愬憳鍒颁細璁?
  const syncTeamToMeeting = useCallback(async (meetingId: number) => {
    try {
      setLoading(true);
      
      const result = await projectMeetingService.syncProjectTeamToMeeting(
        projectId,
        meetingId
      );

      toast({
        title: '鍚屾鎴愬姛',
        description: result.message,
        variant: 'default',
      });

      // 鍒锋柊浼氳鍒楄〃
      await fetchMeetings(
        options.meetingType,
        options.status,
        options.dateRange
      );

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鍚屾鍥㈤槦鎴愬憳澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, fetchMeetings, options, toast]);

  // 涓洪噷绋嬬鍒涘缓璇勫浼氳
  const createMilestoneReviewMeeting = useCallback(async (
    milestoneId: number,
    meetingConfig?: any
  ): Promise<Meeting> => {
    try {
      setLoading(true);
      
      const meeting = await projectMeetingService.createMilestoneReviewMeeting(
        projectId,
        milestoneId,
        meetingConfig
      );

      // 鍒锋柊浼氳鍒楄〃
      await fetchMeetings(
        options.meetingType,
        options.status,
        options.dateRange
      );

      toast({
        title: '成功',
        description: '里程碑评审会议创建成功',
        variant: 'default',
      });

      return meeting;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '创建里程碑评审会议失败';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, fetchMeetings, options, toast]);

  // 鐢熸垚椤圭洰浼氳璁″垝
  const generateMeetingSchedule = useCallback(async (
    config: MeetingScheduleConfig = {}
  ) => {
    try {
      setLoading(true);
      
      const schedule = await projectMeetingService.generateProjectMeetingSchedule(
        projectId,
        config
      );

      return schedule;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鐢熸垚浼氳璁″垝澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, toast]);

  // 灏嗕細璁喅绛栬浆鎹负椤圭洰浠诲姟
  const linkDecisionsToTasks = useCallback(async (
    meetingId: number,
    decisions: MeetingDecision[]
  ) => {
    try {
      setLoading(true);
      
      const result = await projectMeetingService.linkMeetingDecisionsToTasks(
        projectId,
        meetingId,
        decisions
      );

      toast({
        title: '鎴愬姛',
        description: result.message,
        variant: 'default',
      });

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鍒涘缓浠诲姟澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, toast]);

  // 鑾峰彇椤圭洰浼氳缁熻
  const getMeetingStatistics = useCallback(async (
    startDate?: Date,
    endDate?: Date
  ) => {
    try {
      const statistics = await projectMeetingService.getProjectMeetingStatistics(
        projectId,
        startDate,
        endDate
      );

      return statistics;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鑾峰彇缁熻淇℃伅澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    }
  }, [projectId, toast]);

  // 鑾峰彇椤圭洰閫傜敤鐨勪細璁被鍨?
  const getMeetingTypes = useCallback(async () => {
    try {
      const types = await projectMeetingService.getProjectMeetingTypes(projectId);
      return types;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鑾峰彇浼氳绫诲瀷澶辫触';
      setError(errorMessage);
      throw err;
    }
  }, [projectId]);

  // 鍒锋柊浼氳鍒楄〃
  const refreshMeetings = useCallback(() => {
    return fetchMeetings(
      options.meetingType,
      options.status,
      options.dateRange
    );
  }, [fetchMeetings, options]);

  // 鑾峰彇浼氳鐩稿叧浠诲姟
  const getMeetingRelatedTasks = useCallback(async (meetingId: number) => {
    try {
      const result = await projectMeetingService.getMeetingRelatedTasks(
        projectId,
        meetingId
      );
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鑾峰彇浼氳浠诲姟澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    }
  }, [projectId, toast]);

  // 鍚屾浼氳浠诲姟涓庨」鐩换鍔＄郴缁?
  const syncMeetingTasksWithProject = useCallback(async (meetingId: number) => {
    try {
      setLoading(true);
      
      const result = await projectMeetingService.syncMeetingTasksWithProject(
        projectId,
        meetingId
      );

      toast({
        title: '鍚屾鎴愬姛',
        description: result.message,
        variant: 'default',
      });

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鍚屾浠诲姟澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, toast]);

  // 鍏宠仈鐜版湁浠诲姟鍒颁細璁?
  const linkExistingTaskToMeeting = useCallback(async (
    meetingId: number,
    taskId: number
  ) => {
    try {
      setLoading(true);
      
      const result = await projectMeetingService.linkExistingTaskToMeeting(
        projectId,
        meetingId,
        taskId
      );

      toast({
        title: '鍏宠仈鎴愬姛',
        description: result.message,
        variant: 'default',
      });

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鍏宠仈浠诲姟澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, toast]);

  // 鑾峰彇浼氳浠诲姟杩涘害鎽樿
  const getMeetingTaskProgressSummary = useCallback(async (meetingId: number) => {
    try {
      const result = await projectMeetingService.getMeetingTaskProgressSummary(
        projectId,
        meetingId
      );
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鑾峰彇浠诲姟杩涘害澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    }
  }, [projectId, toast]);

  // 鏇存柊浠诲姟杩涘害
  const updateTasksFromMeetingProgress = useCallback(async (
    meetingId: number,
    taskUpdates: Array<{
      task_id: number;
      status?: string;
      actual_hours?: number;
      progress_notes?: string;
    }>
  ) => {
    try {
      setLoading(true);
      
      const result = await projectMeetingService.updateTasksFromMeetingProgress(
        projectId,
        meetingId,
        taskUpdates
      );

      toast({
        title: '鏇存柊鎴愬姛',
        description: result.message,
        variant: 'default',
      });

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '鏇存柊浠诲姟杩涘害澶辫触';
      setError(errorMessage);
      toast({
        title: '閿欒',
        description: errorMessage,
        variant: 'destructive',
      });
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId, toast]);

  // 娓呴櫎閿欒
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // 鑷姩鍔犺浇鏁版嵁
  useEffect(() => {
    if (options.autoLoad !== false && projectId) {
      fetchMeetings(
        options.meetingType,
        options.status,
        options.dateRange
      );
    }
  }, [
    projectId,
    options.autoLoad,
    options.meetingType,
    options.status,
    options.dateRange,
    fetchMeetings
  ]);

  return {
    // 鐘舵€?
    meetings,
    loading,
    error,
    totalCount,
    projectInfo,

    // 鎿嶄綔鏂规硶
    fetchMeetings,
    createProjectMeeting,
    syncTeamToMeeting,
    createMilestoneReviewMeeting,
    generateMeetingSchedule,
    linkDecisionsToTasks,
    getMeetingStatistics,
    getMeetingTypes,
    refreshMeetings,
    clearError,

    // 浠诲姟闆嗘垚鏂规硶
    getMeetingRelatedTasks,
    syncMeetingTasksWithProject,
    linkExistingTaskToMeeting,
    getMeetingTaskProgressSummary,
    updateTasksFromMeetingProgress,
  };
};
