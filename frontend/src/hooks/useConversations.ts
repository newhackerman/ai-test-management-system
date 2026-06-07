/**
 * 对话管理相关的React Hooks
 */
import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  conversationService,
  ConversationResponse,
  ConversationListResponse,
  CreateConversationRequest,
  UpdateConversationRequest,
  SendMessageRequest,
  MessageResponse,
  MessageListResponse,
  SessionStatus,
  ConversationGroup,
  ConversationStatsResponse
} from '../services/conversation-service';

// Query Keys
export const conversationKeys = {
  all: ['conversations'] as const,
  lists: () => [...conversationKeys.all, 'list'] as const,
  list: (filters: Record<string, any>) => [...conversationKeys.lists(), filters] as const,
  details: () => [...conversationKeys.all, 'detail'] as const,
  detail: (id: number) => [...conversationKeys.details(), id] as const,
  messages: (id: number) => [...conversationKeys.all, 'messages', id] as const,
  stats: () => [...conversationKeys.all, 'stats'] as const,
  search: (query: string) => [...conversationKeys.all, 'search', query] as const,
};

/**
 * 获取对话列表
 */
export function useConversations(params: {
  status_filter?: SessionStatus;
  group?: string;
  tags?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  size?: number;
} = {}) {
  return useQuery({
    queryKey: conversationKeys.list(params),
    queryFn: () => conversationService.getConversations(params),
    staleTime: 30000, // 30秒内不重新获取
  });
}

/**
 * 获取对话详情
 */
export function useConversation(conversationId: number | null) {
  return useQuery({
    queryKey: conversationKeys.detail(conversationId!),
    queryFn: () => conversationService.getConversation(conversationId!),
    enabled: !!conversationId,
  });
}

/**
 * 获取对话消息
 */
export function useMessages(conversationId: number | null, params: {
  limit?: number;
  offset?: number;
} = {}) {
  return useQuery({
    queryKey: conversationKeys.messages(conversationId!),
    queryFn: () => conversationService.getMessages(conversationId!, params),
    enabled: !!conversationId,
  });
}

/**
 * 获取对话统计
 */
export function useConversationStats() {
  return useQuery({
    queryKey: conversationKeys.stats(),
    queryFn: () => conversationService.getConversationStats(),
    staleTime: 60000, // 1分钟内不重新获取
  });
}

/**
 * 创建对话
 */
export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateConversationRequest) =>
      conversationService.createConversation(request),
    onSuccess: () => {
      // 刷新对话列表
      queryClient.invalidateQueries({ queryKey: conversationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: conversationKeys.stats() });
    },
  });
}

/**
 * 更新对话
 */
export function useUpdateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ conversationId, request }: {
      conversationId: number;
      request: UpdateConversationRequest;
    }) => conversationService.updateConversation(conversationId, request),
    onSuccess: (data, variables) => {
      // 更新缓存
      queryClient.setQueryData(
        conversationKeys.detail(variables.conversationId),
        data
      );
      // 刷新列表
      queryClient.invalidateQueries({ queryKey: conversationKeys.lists() });
    },
  });
}

/**
 * 删除对话
 */
export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: number) =>
      conversationService.deleteConversation(conversationId),
    onSuccess: (_, conversationId) => {
      // 移除详情缓存
      queryClient.removeQueries({ queryKey: conversationKeys.detail(conversationId) });
      // 刷新列表
      queryClient.invalidateQueries({ queryKey: conversationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: conversationKeys.stats() });
    },
  });
}

/**
 * 归档对话
 */
export function useArchiveConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: number) =>
      conversationService.archiveConversation(conversationId),
    onSuccess: () => {
      // 刷新列表
      queryClient.invalidateQueries({ queryKey: conversationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: conversationKeys.stats() });
    },
  });
}

/**
 * 发送消息
 */
export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ conversationId, request }: {
      conversationId: number;
      request: SendMessageRequest;
    }) => conversationService.sendMessage(conversationId, request),
    onSuccess: (data, variables) => {
      // 刷新消息列表
      queryClient.invalidateQueries({
        queryKey: conversationKeys.messages(variables.conversationId)
      });
      // 刷新对话详情（更新消息计数等）
      queryClient.invalidateQueries({
        queryKey: conversationKeys.detail(variables.conversationId)
      });
      // 刷新对话列表（更新最后活动时间）
      queryClient.invalidateQueries({ queryKey: conversationKeys.lists() });
    },
  });
}

/**
 * 搜索对话
 */
export function useSearchConversations() {
  const [searchResults, setSearchResults] = useState<ConversationListResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<Error | null>(null);

  const searchConversations = useCallback(async (params: {
    query: string;
    status?: SessionStatus;
    group?: ConversationGroup;
    tags?: string[];
    page?: number;
    size?: number;
  }) => {
    if (!params.query.trim()) {
      setSearchResults(null);
      return;
    }

    setIsSearching(true);
    setSearchError(null);

    try {
      const results = await conversationService.searchConversations(params);
      setSearchResults(results);
    } catch (error) {
      setSearchError(error as Error);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const clearSearch = useCallback(() => {
    setSearchResults(null);
    setSearchError(null);
  }, []);

  return {
    searchResults,
    isSearching,
    searchError,
    searchConversations,
    clearSearch,
  };
}

/**
 * 对话管理状态Hook
 */
export function useConversationManager() {
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const createMutation = useCreateConversation();
  const updateMutation = useUpdateConversation();
  const deleteMutation = useDeleteConversation();
  const archiveMutation = useArchiveConversation();

  const createConversation = useCallback(async (request: CreateConversationRequest) => {
    setIsCreating(true);
    try {
      const result = await createMutation.mutateAsync(request);
      setSelectedConversationId(result.id);
      return result;
    } finally {
      setIsCreating(false);
    }
  }, [createMutation]);

  const updateConversation = useCallback(async (
    conversationId: number,
    request: UpdateConversationRequest
  ) => {
    setIsEditing(true);
    try {
      return await updateMutation.mutateAsync({ conversationId, request });
    } finally {
      setIsEditing(false);
    }
  }, [updateMutation]);

  const deleteConversation = useCallback(async (conversationId: number) => {
    await deleteMutation.mutateAsync(conversationId);
    if (selectedConversationId === conversationId) {
      setSelectedConversationId(null);
    }
  }, [deleteMutation, selectedConversationId]);

  const archiveConversation = useCallback(async (conversationId: number) => {
    await archiveMutation.mutateAsync(conversationId);
  }, [archiveMutation]);

  return {
    selectedConversationId,
    setSelectedConversationId,
    isCreating,
    isEditing,
    createConversation,
    updateConversation,
    deleteConversation,
    archiveConversation,
    isLoading: createMutation.isPending || updateMutation.isPending || 
               deleteMutation.isPending || archiveMutation.isPending,
    error: createMutation.error || updateMutation.error || 
           deleteMutation.error || archiveMutation.error,
  };
}