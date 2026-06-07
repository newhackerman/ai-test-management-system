/**
 * 对话管理服务
 */
import { apiClient } from '../lib/api-client';

const unwrapResponse = <T>(response: unknown): T => {
  const payload = response as T | { data?: T };
  if (payload && typeof payload === 'object' && 'data' in payload) {
    return (payload as { data?: T }).data as T;
  }
  return payload as T;
};

export interface CreateConversationRequest {
  title?: string;
  ai_provider?: string;
  ai_model?: string;
  system_prompt?: string;
  template_type?: string;
  group?: ConversationGroup;
  tags?: string[];
  goal?: string;
}

export interface ConversationResponse {
  id: number;
  title: string;
  user_id: number;
  status: SessionStatus;
  ai_provider?: string;
  ai_model?: string;
  system_prompt?: string;
  message_count: number;
  total_tokens: number;
  last_activity_at: string;
  tags?: string[];
  session_metadata?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface ConversationListResponse {
  success: boolean;
  conversations: ConversationResponse[];
  total_count: number;
  page: number;
  size: number;
  total_pages: number;
}

export interface UpdateConversationRequest {
  title?: string;
  ai_provider?: string;
  ai_model?: string;
  system_prompt?: string;
  tags?: string[];
  status?: SessionStatus;
}

export interface SendMessageRequest {
  content: string;
  content_type?: ContentType;
  metadata?: Record<string, any>;
}

export interface MessageResponse {
  id: number;
  session_id: number;
  role: MessageRole;
  content: string;
  content_type: ContentType;
  ai_provider?: string;
  ai_model?: string;
  tokens_used: number;
  confidence_score?: number;
  is_streaming: boolean;
  is_error: boolean;
  error_message?: string;
  message_metadata?: Record<string, any>;
  parent_message_id?: number;
  user_rating?: number;
  user_feedback?: string;
  is_bookmarked: boolean;
  created_at: string;
  updated_at?: string;
}

export interface MessageListResponse {
  success: boolean;
  messages: MessageResponse[];
  total_count: number;
  conversation_id: number;
}

export interface ConversationStatsResponse {
  total_conversations: number;
  active_conversations: number;
  archived_conversations: number;
  total_messages: number;
  total_tokens: number;
  avg_messages_per_conversation: number;
  most_used_provider?: string;
  most_used_model?: string;
}

export enum SessionStatus {
  ACTIVE = 'ACTIVE',
  ARCHIVED = 'ARCHIVED',
  DELETED = 'DELETED'
}

export enum ConversationGroup {
  WORK = 'work',
  STUDY = 'study',
  PROJECT = 'project',
  PERSONAL = 'personal',
  RESEARCH = 'research',
  DEVELOPMENT = 'development',
  TESTING = 'testing',
  OTHER = 'other'
}

export enum MessageRole {
  USER = 'USER',
  ASSISTANT = 'ASSISTANT',
  SYSTEM = 'SYSTEM'
}

export enum ContentType {
  TEXT = 'TEXT',
  MARKDOWN = 'MARKDOWN',
  CODE = 'CODE',
  IMAGE = 'IMAGE',
  FILE = 'FILE'
}

export class ConversationService {
  private baseUrl = '/api/v1/ai-assistant';

  /**
   * 创建新对话
   */
  async createConversation(request: CreateConversationRequest): Promise<ConversationResponse> {
    const response = await apiClient.post<ConversationResponse>(
      `${this.baseUrl}/conversations`,
      request
    );
    return unwrapResponse<ConversationResponse>(response);
  }

  /**
   * 获取对话列表
   */
  async getConversations(params: {
    status_filter?: SessionStatus;
    group?: string;
    tags?: string;
    sort_by?: string;
    sort_order?: string;
    page?: number;
    size?: number;
  } = {}): Promise<ConversationListResponse> {
    const response = await apiClient.get<ConversationListResponse>(
      `${this.baseUrl}/conversations`,
      { params }
    );
    return unwrapResponse<ConversationListResponse>(response) || {
      success: true,
      conversations: [],
      total_count: 0,
      page: params.page || 1,
      size: params.size || 20,
      total_pages: 0
    };
  }

  /**
   * 获取对话详情
   */
  async getConversation(conversationId: number): Promise<ConversationResponse> {
    const response = await apiClient.get<ConversationResponse>(
      `${this.baseUrl}/conversations/${conversationId}`
    );
    return unwrapResponse<ConversationResponse>(response);
  }

  /**
   * 更新对话
   */
  async updateConversation(
    conversationId: number,
    request: UpdateConversationRequest
  ): Promise<ConversationResponse> {
    const response = await apiClient.put<ConversationResponse>(
      `${this.baseUrl}/conversations/${conversationId}`,
      request
    );
    return unwrapResponse<ConversationResponse>(response);
  }

  /**
   * 删除对话
   */
  async deleteConversation(conversationId: number): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete<{ success: boolean; message: string }>(
      `${this.baseUrl}/conversations/${conversationId}`
    );
    return unwrapResponse<{ success: boolean; message: string }>(response);
  }

  /**
   * 归档对话
   */
  async archiveConversation(conversationId: number): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post<{ success: boolean; message: string }>(
      `${this.baseUrl}/conversations/${conversationId}/archive`
    );
    return unwrapResponse<{ success: boolean; message: string }>(response);
  }

  /**
   * 发送消息
   */
  async sendMessage(
    conversationId: number,
    request: SendMessageRequest
  ): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>(
      `${this.baseUrl}/conversations/${conversationId}/messages`,
      request
    );
    return unwrapResponse<MessageResponse>(response);
  }

  /**
   * 获取消息列表
   */
  async getMessages(
    conversationId: number,
    params: {
      limit?: number;
      offset?: number;
    } = {}
  ): Promise<MessageListResponse> {
    const response = await apiClient.get<MessageListResponse>(
      `${this.baseUrl}/conversations/${conversationId}/messages`,
      { params }
    );
    return unwrapResponse<MessageListResponse>(response) || {
      success: true,
      messages: [],
      total_count: 0,
      conversation_id: conversationId
    };
  }

  /**
   * 搜索对话
   */
  async searchConversations(params: {
    query: string;
    status?: SessionStatus;
    group?: ConversationGroup;
    tags?: string[];
    page?: number;
    size?: number;
  }): Promise<ConversationListResponse> {
    const response = await apiClient.get<ConversationListResponse>(
      `${this.baseUrl}/conversations/search`,
      { params }
    );
    return unwrapResponse<ConversationListResponse>(response);
  }

  /**
   * 获取对话统计
   */
  async getConversationStats(): Promise<ConversationStatsResponse> {
    const response = await apiClient.get<ConversationStatsResponse>(
      `${this.baseUrl}/conversations/stats`
    );
    return unwrapResponse<ConversationStatsResponse>(response) || {
      total_conversations: 0,
      active_conversations: 0,
      archived_conversations: 0,
      total_messages: 0,
      total_tokens: 0,
      avg_messages_per_conversation: 0
    };
  }
}

export const conversationService = new ConversationService();
