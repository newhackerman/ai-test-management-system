// @ts-nocheck
/**
 * 椤圭洰浼氳鏈嶅姟
 * 
 * 鎻愪緵椤圭洰浼氳鐩稿叧鐨凙PI璋冪敤鍔熻兘锛屽寘鎷細
 * - 椤圭洰浼氳绠＄悊
 * - 鍥㈤槦鍚屾
 * - 浼氳璁″垝鐢熸垚
 * - 缁熻鍒嗘瀽
 */
import { apiClient } from '@/services/api/apiClient';
import { Meeting, CreateProjectMeetingRequest } from '@/types/meeting';

export interface ProjectMeetingListParams {
  meeting_type?: string;
  status?: string;
  start_date?: Date;
  end_date?: Date;
}

export interface ProjectMeetingListResponse {
  meetings: Meeting[];
  total_count: number;
  project_info: {
    id: number;
    name: string;
    code: string;
    status: string;
  };
}

export interface TeamSyncResult {
  total_project_members: number;
  existing_participants: number;
  added_participants: number;
  success: boolean;
  message: string;
}

export interface MeetingScheduleConfig {
  weekly_sync?: boolean;
  milestone_reviews?: boolean;
  task_reviews?: boolean;
  auto_create_kickoff?: boolean;
}

export interface MeetingScheduleItem {
  type: string;
  title: string;
  scheduled_date: string;
  duration: number;
  priority: string;
  auto_create: boolean;
  milestone_id?: number;
  task_id?: number;
  recurring?: boolean;
}

export interface MeetingScheduleResponse {
  schedule: MeetingScheduleItem[];
  project_info: any;
  total_meetings: number;
}

export interface MeetingDecision {
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

export interface TaskCreationResult {
  created_task_ids: number[];
  total_decisions: number;
  tasks_created: number;
  success: boolean;
  message: string;
}

export interface MeetingStatistics {
  project_id: number;
  total_meetings: number;
  completed_meetings: number;
  completion_rate: number;
  total_duration_minutes: number;
  avg_duration_minutes: number;
  type_statistics: Record<string, { count: number; duration: number }>;
  status_statistics: Record<string, number>;
  date_range: {
    start_date?: string;
    end_date?: string;
  };
}

export interface MeetingType {
  value: string;
  label: string;
  description: string;
  default_duration: number;
  recommended_participants: string[];
}

class ProjectMeetingService {
  private baseUrl = '/api/v1/meetings/projects';

  /**
   * 涓洪」鐩垱寤轰細璁?
   */
  async createProjectMeeting(
    projectId: number,
    meetingData: CreateProjectMeetingRequest
  ): Promise<Meeting> {
    const response = await apiClient.post<Meeting>(
      `${this.baseUrl}/${projectId}/meetings`,
      meetingData
    );
    return response.data;
  }

  /**
   * 鑾峰彇椤圭洰浼氳鍒楄〃
   */
  async getProjectMeetings(
    projectId: number,
    params: ProjectMeetingListParams = {}
  ): Promise<ProjectMeetingListResponse> {
    const queryParams = new URLSearchParams();
    
    if (params.meeting_type) {
      queryParams.append('meeting_type', params.meeting_type);
    }
    if (params.status) {
      queryParams.append('status', params.status);
    }
    if (params.start_date) {
      queryParams.append('start_date', params.start_date.toISOString().split('T')[0]);
    }
    if (params.end_date) {
      queryParams.append('end_date', params.end_date.toISOString().split('T')[0]);
    }

    const url = `${this.baseUrl}/${projectId}/meetings${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    const response = await apiClient.get<ProjectMeetingListResponse>(url);
    return response.data;
  }

  /**
   * 鍚屾椤圭洰鍥㈤槦鎴愬憳鍒颁細璁?
   */
  async syncProjectTeamToMeeting(
    projectId: number,
    meetingId: number
  ): Promise<TeamSyncResult> {
    const response = await apiClient.post<TeamSyncResult>(
      `${this.baseUrl}/${projectId}/meetings/${meetingId}/sync-team`
    );
    return response.data;
  }

  /**
   * 涓洪噷绋嬬鍒涘缓璇勫浼氳
   */
  async createMilestoneReviewMeeting(
    projectId: number,
    milestoneId: number,
    meetingConfig?: any
  ): Promise<Meeting> {
    const response = await apiClient.post<Meeting>(
      `${this.baseUrl}/${projectId}/milestones/${milestoneId}/meeting`,
      meetingConfig || {}
    );
    return response.data;
  }

  /**
   * 鐢熸垚椤圭洰浼氳璁″垝
   */
  async generateProjectMeetingSchedule(
    projectId: number,
    config: MeetingScheduleConfig = {}
  ): Promise<MeetingScheduleResponse> {
    const queryParams = new URLSearchParams();
    
    if (config.weekly_sync !== undefined) {
      queryParams.append('weekly_sync', config.weekly_sync.toString());
    }
    if (config.milestone_reviews !== undefined) {
      queryParams.append('milestone_reviews', config.milestone_reviews.toString());
    }
    if (config.task_reviews !== undefined) {
      queryParams.append('task_reviews', config.task_reviews.toString());
    }
    if (config.auto_create_kickoff !== undefined) {
      queryParams.append('auto_create_kickoff', config.auto_create_kickoff.toString());
    }

    const url = `${this.baseUrl}/${projectId}/meeting-schedule${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    const response = await apiClient.get<MeetingScheduleResponse>(url);
    return response.data;
  }

  /**
   * 灏嗕細璁喅绛栬浆鎹负椤圭洰浠诲姟
   */
  async linkMeetingDecisionsToTasks(
    projectId: number,
    meetingId: number,
    decisions: MeetingDecision[]
  ): Promise<TaskCreationResult> {
    const response = await apiClient.post<TaskCreationResult>(
      `${this.baseUrl}/${projectId}/meetings/${meetingId}/decisions-to-tasks`,
      { decisions }
    );
    return response.data;
  }

  /**
   * 鑾峰彇椤圭洰閫傜敤鐨勪細璁被鍨?
   */
  async getProjectMeetingTypes(projectId: number): Promise<{
    meeting_types: MeetingType[];
    project_id: number;
  }> {
    const response = await apiClient.get<{
      meeting_types: MeetingType[];
      project_id: number;
    }>(`${this.baseUrl}/${projectId}/meeting-types`);
    return response.data;
  }

  /**
   * 鑾峰彇椤圭洰浼氳缁熻淇℃伅
   */
  async getProjectMeetingStatistics(
    projectId: number,
    startDate?: Date,
    endDate?: Date
  ): Promise<MeetingStatistics> {
    const queryParams = new URLSearchParams();
    
    if (startDate) {
      queryParams.append('start_date', startDate.toISOString().split('T')[0]);
    }
    if (endDate) {
      queryParams.append('end_date', endDate.toISOString().split('T')[0]);
    }

    const url = `${this.baseUrl}/${projectId}/meeting-statistics${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    const response = await apiClient.get<MeetingStatistics>(url);
    return response.data;
  }

  /**
   * 鎵归噺鍒涘缓浼氳璁″垝涓殑浼氳
   */
  async createScheduledMeetings(
    projectId: number,
    scheduleItems: MeetingScheduleItem[]
  ): Promise<Meeting[]> {
    const createdMeetings: Meeting[] = [];
    
    for (const item of scheduleItems) {
      if (item.auto_create) {
        try {
          const meetingData: CreateProjectMeetingRequest = {
            title: item.title,
            meeting_type: item.type,
            scheduled_start_time: new Date(item.scheduled_date),
            scheduled_end_time: new Date(
              new Date(item.scheduled_date).getTime() + item.duration * 60000
            ),
            auto_invite_team: true,
          };

          const meeting = await this.createProjectMeeting(projectId, meetingData);
          createdMeetings.push(meeting);
        } catch (error) {
          console.error(`鍒涘缓浼氳澶辫触: ${item.title}`, error);
        }
      }
    }

    return createdMeetings;
  }

  /**
   * 鑾峰彇椤圭洰浼氳鏃ュ巻鏁版嵁
   */
  async getProjectMeetingCalendar(
    projectId: number,
    year: number,
    month: number
  ): Promise<{
    meetings: Meeting[];
    calendar_data: any[];
  }> {
    const startDate = new Date(year, month - 1, 1);
    const endDate = new Date(year, month, 0);

    const response = await this.getProjectMeetings(projectId, {
      start_date: startDate,
      end_date: endDate,
    });

    // 杞崲涓烘棩鍘嗘暟鎹牸寮?
    const calendarData = response.meetings.map(meeting => ({
      id: meeting.id,
      title: meeting.title,
      start: meeting.scheduled_start_time,
      end: meeting.scheduled_end_time,
      type: meeting.meeting_type,
      status: meeting.status,
      participants: meeting.participant_count,
    }));

    return {
      meetings: response.meetings,
      calendar_data: calendarData,
    };
  }

  /**
   * 瀵煎嚭椤圭洰浼氳鎶ュ憡
   */
  async exportProjectMeetingReport(
    projectId: number,
    format: 'excel' | 'pdf' = 'excel',
    dateRange?: { start: Date; end: Date }
  ): Promise<Blob> {
    const queryParams = new URLSearchParams();
    queryParams.append('format', format);
    
    if (dateRange) {
      queryParams.append('start_date', dateRange.start.toISOString().split('T')[0]);
      queryParams.append('end_date', dateRange.end.toISOString().split('T')[0]);
    }

    const response = await apiClient.get(
      `${this.baseUrl}/${projectId}/export-report?${queryParams.toString()}`,
      { responseType: 'blob' }
    );

    return response.data;
  }

  /**
   * 鑾峰彇浼氳鐩稿叧鐨勪换鍔″垪琛?
   */
  async getMeetingRelatedTasks(
    projectId: number,
    meetingId: number
  ): Promise<{
    meeting_id: number;
    project_id: number;
    tasks: any[];
    total_count: number;
  }> {
    const response = await apiClient.get(
      `${this.baseUrl}/${projectId}/meetings/${meetingId}/tasks`
    );
    return response.data;
  }

  /**
   * 鍚屾浼氳浠诲姟涓庨」鐩换鍔＄郴缁?
   */
  async syncMeetingTasksWithProject(
    projectId: number,
    meetingId: number
  ): Promise<{
    success: boolean;
    message: string;
    meeting_id: number;
    project_id: number;
    total_project_tasks: number;
    linked_tasks: number;
    unlinked_tasks: number;
    linked_task_details: any[];
    suggested_links: any[];
  }> {
    const response = await apiClient.post(
      `${this.baseUrl}/${projectId}/meetings/${meetingId}/tasks/sync`
    );
    return response.data;
  }

  /**
   * 灏嗙幇鏈変换鍔″叧鑱斿埌浼氳
   */
  async linkExistingTaskToMeeting(
    projectId: number,
    meetingId: number,
    taskId: number
  ): Promise<{
    success: boolean;
    message: string;
    task: any;
  }> {
    const response = await apiClient.post(
      `${this.baseUrl}/${projectId}/meetings/${meetingId}/tasks/${taskId}/link`
    );
    return response.data;
  }

  /**
   * 鑾峰彇浼氳浠诲姟杩涘害鎽樿
   */
  async getMeetingTaskProgressSummary(
    projectId: number,
    meetingId: number
  ): Promise<{
    meeting_id: number;
    total_tasks: number;
    progress_summary: {
      completion_rate: number;
      status_distribution: Record<string, number>;
      estimated_hours: number;
      actual_hours: number;
      hours_progress: number;
    };
    task_details: any[];
  }> {
    const response = await apiClient.get(
      `${this.baseUrl}/${projectId}/meetings/${meetingId}/tasks/progress`
    );
    return response.data;
  }

  /**
   * 鏍规嵁浼氳杩涘睍鏇存柊浠诲姟鐘舵€?
   */
  async updateTasksFromMeetingProgress(
    projectId: number,
    meetingId: number,
    taskUpdates: Array<{
      task_id: number;
      status?: string;
      actual_hours?: number;
      progress_notes?: string;
    }>
  ): Promise<{
    success: boolean;
    message: string;
    updated_tasks: any[];
  }> {
    const response = await apiClient.put(
      `${this.baseUrl}/${projectId}/meetings/${meetingId}/tasks/update-progress`,
      taskUpdates
    );
    return response.data;
  }
}

export const projectMeetingService = new ProjectMeetingService();