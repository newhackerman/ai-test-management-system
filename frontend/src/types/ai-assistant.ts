/**
 * AI助手模块前端TypeScript类型定义
 * 与后端API接口规范保持一致
 */

// ============================================================================
// 基础响应格式
// ============================================================================

export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: {
    code: string;
    details: string;
    field?: string;
  };
}

export interface ErrorDetail {
  code: string;
  details: string;
  field?: string;
}

// ============================================================================
// 对话相关数据结构
// ============================================================================

export type MessageRole = 'USER' | 'ASSISTANT' | 'SYSTEM';
export type ContentType = 'TEXT' | 'MARKDOWN' | 'CODE' | 'JSON';
export type ConversationStatus = 'ACTIVE' | 'ARCHIVED' | 'DELETED';

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: MessageRole;
  content: string;
  content_type: ContentType;
  ai_provider?: string;
  tokens_used?: number;
  confidence_score?: number;
  created_at: string;
  updated_at?: string;
  metadata?: Record<string, any>;
}

export interface Conversation {
  id: number;
  user_id: number;
  title: string;
  status: ConversationStatus;
  ai_provider?: string;
  ai_model?: string;
  message_count: number;
  total_tokens: number;
  created_at: string;
  updated_at?: string;
  last_message_at?: string;
  metadata?: Record<string, any>;
}

// ============================================================================
// 建议相关数据结构
// ============================================================================

export const SuggestionType = {
  OPTIMIZATION: 'OPTIMIZATION',
  IMPROVEMENT: 'IMPROVEMENT',
  RISK_MITIGATION: 'RISK_MITIGATION',
  QUALITY_ENHANCEMENT: 'QUALITY_ENHANCEMENT',
  PROCESS_IMPROVEMENT: 'PROCESS_IMPROVEMENT'
} as const;
export type SuggestionType = typeof SuggestionType[keyof typeof SuggestionType];

export const SuggestionStatus = {
  PENDING: 'PENDING',
  ACCEPTED: 'ACCEPTED',
  REJECTED: 'REJECTED',
  IMPLEMENTED: 'IMPLEMENTED',
  CANCELLED: 'CANCELLED'
} as const;
export type SuggestionStatus = typeof SuggestionStatus[keyof typeof SuggestionStatus];

export const SuggestionPriority = {
  LOW: 'LOW',
  MEDIUM: 'MEDIUM',
  HIGH: 'HIGH',
  CRITICAL: 'CRITICAL'
} as const;
export type SuggestionPriority = typeof SuggestionPriority[keyof typeof SuggestionPriority];

export interface Suggestion {
  id: number;
  title: string;
  description: string;
  type: SuggestionType;
  status: SuggestionStatus;
  priority: SuggestionPriority;
  
  user_id: number;
  project_id?: number;
  conversation_id?: number;
  
  action_items?: string[];
  expected_benefit?: string;
  estimated_effort?: string;
  implementation_notes?: string;
  
  ai_provider?: string;
  ai_model?: string;
  confidence_score?: number;
  
  user_rating?: number;
  user_feedback?: string;
  
  implemented_at?: string;
  implemented_by?: number;
  implementation_result?: string;
  
  created_at: string;
  updated_at?: string;
  metadata?: Record<string, any>;
  
  // 客户端状态管理字段
  _syncing?: boolean;
  _lastSynced?: string;
  _localChanges?: boolean;
}

// ============================================================================
// 需求分析相关数据结构
// ============================================================================

export interface RequirementIssue {
  requirement_id: number | string;
  requirement_title: string;
  issue_type: string;
  description: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  suggestions: string[];
}

export interface QualityMetrics {
  completeness_score: number;
  clarity_score: number;
  consistency_score: number;
  testability_score: number;
  overall_score: number;
}

export interface RequirementsAnalysisResult {
  analysis_id: string;
  project_id: number;
  total_requirements: number;
  quality_metrics: QualityMetrics;
  issues: RequirementIssue[];
  suggestions: any[];
  analysis_summary: string;
  created_at: string;
  completed_at?: string;
}

// ============================================================================
// 分析进度相关数据结构
// ============================================================================

export type AnalysisStatus = 
  | 'PENDING' 
  | 'ANALYZING' 
  | 'COMPLETED' 
  | 'FAILED' 
  | 'CANCELLED';

export interface AnalysisProgress {
  analysis_id: string;
  project_id: number;
  status: AnalysisStatus;
  progress: number; // 0-100
  current_step: string;
  estimated_time_remaining: number; // seconds
  completed_steps: string[];
  total_steps: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// WebSocket消息格式
// ============================================================================

export type WSMessageType = 
  | 'message' 
  | 'typing' 
  | 'status' 
  | 'error'
  | 'analysis_progress'
  | 'analysis_result'
  | 'analysis_error'
  | 'suggestion_update';

export interface WSMessage {
  type: WSMessageType;
  conversation_id?: number;
  data: any;
  timestamp: string;
  user_id?: number;
  metadata?: Record<string, any>;
}

// ============================================================================
// 状态同步相关数据结构
// ============================================================================

export type ConnectionStatus = 
  | 'connected' 
  | 'disconnected' 
  | 'connecting' 
  | 'reconnecting';

export type SyncStatus = 'synced' | 'syncing' | 'error' | 'offline';

export interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: ChatMessage[];
  loading: boolean;
  connectionStatus: ConnectionStatus;
  syncStatus: SyncStatus;
  typingUsers: number[];
}

export type BatchOperationStatus = 
  | 'PENDING' 
  | 'PROCESSING' 
  | 'COMPLETED' 
  | 'FAILED' 
  | 'PARTIAL_SUCCESS';

export interface BatchProgress {
  operation_id: string;
  status: BatchOperationStatus;
  total_items: number;
  processed_items: number;
  successful_items: number;
  failed_items: number;
  progress_percentage: number;
  error_messages: string[];
  started_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface BatchOperationProgress {
  total: number;
  completed: number;
  failed: number;
  progress: number; // 0-100
  status: 'pending' | 'processing' | 'completed' | 'failed';
  errors: string[];
}

// ============================================================================
// 请求和响应模式
// ============================================================================

export interface CreateConversationRequest {
  title?: string;
  ai_provider?: string;
  ai_model?: string;
  initial_message?: string;
}

export interface SendMessageRequest {
  content: string;
  content_type?: ContentType;
  metadata?: Record<string, any>;
}

export interface UpdateSuggestionRequest {
  status?: SuggestionStatus;
  user_rating?: number;
  user_feedback?: string;
  implementation_notes?: string;
}

export interface BatchUpdateSuggestionsRequest {
  suggestion_ids: number[];
  updates: UpdateSuggestionRequest;
  operation_reason?: string;
}

export interface StartAnalysisRequest {
  project_id: number;
  requirements: any[];
  analysis_options?: Record<string, any>;
  include_ai_analysis?: boolean;
}

// ============================================================================
// 分页和过滤
// ============================================================================

export interface PaginationParams {
  page?: number;
  size?: number;
}

export interface SuggestionFilters {
  status?: SuggestionStatus[];
  type?: SuggestionType[];
  priority?: SuggestionPriority[];
  project_id?: number;
  date_from?: string;
  date_to?: string;
  search_text?: string;
  min_rating?: number;
  has_feedback?: boolean;
  implemented?: boolean;
}

export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// ============================================================================
// 组件Props类型
// ============================================================================

export interface ChatInterfaceProps {
  conversation?: Conversation;
  onSendMessage?: (message: string) => void;
  onNewConversation?: () => void;
  className?: string;
}

export interface MessageBubbleProps {
  message: ChatMessage;
  isOwn?: boolean;
  showAvatar?: boolean;
  onEdit?: (messageId: number, content: string) => void;
  onDelete?: (messageId: number) => void;
  onCopy?: (content: string) => void;
  className?: string;
}

export interface MessageInputProps {
  onSend: (content: string, contentType?: ContentType) => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  supportedTypes?: ContentType[];
  className?: string;
}

export interface SuggestionCardProps {
  suggestion: Suggestion;
  onAccept?: (suggestionId: number) => void;
  onReject?: (suggestionId: number) => void;
  onRate?: (suggestionId: number, rating: number) => void;
  onFeedback?: (suggestionId: number, feedback: string) => void;
  showActions?: boolean;
  className?: string;
}

export interface SuggestionManagementProps {
  projectId?: number;
  filters?: SuggestionFilters;
  onFiltersChange?: (filters: SuggestionFilters) => void;
  onBatchUpdate?: (suggestionIds: number[], updates: UpdateSuggestionRequest) => void;
  className?: string;
}

export interface RequirementsAnalysisProps {
  projectId: number;
  requirements: any[];
  onAnalysisComplete?: (result: RequirementsAnalysisResult) => void;
  onProgressUpdate?: (progress: AnalysisProgress) => void;
  className?: string;
}

export interface QualityScoreCardProps {
  metrics: QualityMetrics;
  showDetails?: boolean;
  onDetailClick?: (metric: keyof QualityMetrics) => void;
  className?: string;
}

// ============================================================================
// Hook返回类型
// ============================================================================

export interface UseChatReturn {
  // 状态
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: ChatMessage[];
  loading: boolean;
  connectionStatus: ConnectionStatus;
  syncStatus: SyncStatus;
  
  // 操作
  createConversation: (request: CreateConversationRequest) => Promise<Conversation>;
  selectConversation: (conversationId: number) => Promise<void>;
  sendMessage: (content: string, contentType?: ContentType) => Promise<ChatMessage>;
  deleteConversation: (conversationId: number) => Promise<void>;
  
  // WebSocket
  connect: () => void;
  disconnect: () => void;
  
  // 错误处理
  error: string | null;
  clearError: () => void;
}

export interface UseSuggestionsReturn {
  // 状态
  suggestions: Suggestion[];
  loading: boolean;
  error: string | null;
  
  // 分页
  pagination: {
    page: number;
    size: number;
    total: number;
    pages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
  
  // 操作
  loadSuggestions: (filters?: SuggestionFilters, pagination?: PaginationParams) => Promise<void>;
  acceptSuggestion: (suggestionId: number) => Promise<void>;
  rejectSuggestion: (suggestionId: number) => Promise<void>;
  rateSuggestion: (suggestionId: number, rating: number) => Promise<void>;
  batchUpdate: (suggestionIds: number[], updates: UpdateSuggestionRequest) => Promise<BatchProgress>;
  
  // 过滤
  filters: SuggestionFilters;
  setFilters: (filters: SuggestionFilters) => void;
  
  // 错误处理
  clearError: () => void;
}

export interface UseAnalysisReturn {
  // 状态
  analysisResult: RequirementsAnalysisResult | null;
  progress: AnalysisProgress | null;
  loading: boolean;
  error: string | null;
  
  // 操作
  startAnalysis: (request: StartAnalysisRequest) => Promise<string>;
  cancelAnalysis: (analysisId: string) => Promise<void>;
  getAnalysisResult: (analysisId: string) => Promise<RequirementsAnalysisResult>;
  
  // 错误处理
  clearError: () => void;
}

// ============================================================================
// 服务类型
// ============================================================================

export interface AIAssistantService {
  // 对话管理
  createConversation(request: CreateConversationRequest): Promise<APIResponse<Conversation>>;
  getConversations(pagination?: PaginationParams): Promise<APIResponse<PaginatedResponse<Conversation>>>;
  getConversation(conversationId: number): Promise<APIResponse<Conversation>>;
  deleteConversation(conversationId: number): Promise<APIResponse<void>>;
  
  // 消息管理
  sendMessage(conversationId: number, request: SendMessageRequest): Promise<APIResponse<ChatMessage>>;
  getMessages(conversationId: number, pagination?: PaginationParams): Promise<APIResponse<PaginatedResponse<ChatMessage>>>;
  
  // 建议管理
  getSuggestions(filters?: SuggestionFilters, pagination?: PaginationParams): Promise<APIResponse<PaginatedResponse<Suggestion>>>;
  updateSuggestion(suggestionId: number, request: UpdateSuggestionRequest): Promise<APIResponse<Suggestion>>;
  batchUpdateSuggestions(request: BatchUpdateSuggestionsRequest): Promise<APIResponse<BatchProgress>>;
  
  // 需求分析
  startAnalysis(request: StartAnalysisRequest): Promise<APIResponse<{ analysis_id: string }>>;
  getAnalysisProgress(analysisId: string): Promise<APIResponse<AnalysisProgress>>;
  getAnalysisResult(analysisId: string): Promise<APIResponse<RequirementsAnalysisResult>>;
}

export interface WebSocketService {
  connect(userId: number): void;
  disconnect(): void;
  subscribe(messageType: WSMessageType, callback: (message: WSMessage) => void): void;
  unsubscribe(messageType: WSMessageType, callback: (message: WSMessage) => void): void;
  send(message: WSMessage): void;
  getConnectionStatus(): ConnectionStatus;
}

// ============================================================================
// 状态管理类型
// ============================================================================

export interface AIAssistantState {
  // 对话状态
  chat: ChatState;
  
  // 建议状态
  suggestions: {
    items: Suggestion[];
    loading: boolean;
    error: string | null;
    filters: SuggestionFilters;
    pagination: PaginationParams & {
      total: number;
      pages: number;
      hasNext: boolean;
      hasPrev: boolean;
    };
  };
  
  // 分析状态
  analysis: {
    currentAnalysis: RequirementsAnalysisResult | null;
    progress: AnalysisProgress | null;
    loading: boolean;
    error: string | null;
  };
  
  // 全局状态
  connectionStatus: ConnectionStatus;
  syncStatus: SyncStatus;
  user: {
    id: number;
    name: string;
    avatar?: string;
  } | null;
}

// ============================================================================
// 事件类型
// ============================================================================

export interface ChatEvents {
  'message:sent': { message: ChatMessage };
  'message:received': { message: ChatMessage };
  'conversation:created': { conversation: Conversation };
  'conversation:selected': { conversation: Conversation };
  'connection:status': { status: ConnectionStatus };
  'sync:status': { status: SyncStatus };
  'error': { error: string };
}

export interface SuggestionEvents {
  'suggestion:updated': { suggestion: Suggestion };
  'suggestion:accepted': { suggestionId: number };
  'suggestion:rejected': { suggestionId: number };
  'batch:progress': { progress: BatchProgress };
  'batch:completed': { operationId: string };
}

export interface AnalysisEvents {
  'analysis:started': { analysisId: string };
  'analysis:progress': { progress: AnalysisProgress };
  'analysis:completed': { result: RequirementsAnalysisResult };
  'analysis:failed': { analysisId: string; error: string };
}

// ============================================================================
// 工具类型
// ============================================================================

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

export type OptionalFields<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

// 导出所有类型
export * from './ai-assistant';
