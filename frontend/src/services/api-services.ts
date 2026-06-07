// @ts-nocheck
// API鏈嶅姟灞?- 瀹屾暣瀹炵幇

import { apiClient } from '@/lib/api-client'
import type {
  User,
  Project,
  TestCase,
  TestResult,
  DashboardStats,
  PerformanceTest,
  SecurityScan,
  AIAnalysis,
  SystemConfig,
  Notification,
  PaginatedResponse,
  ApiResponse
} from '@/types'

/**
 * 璁よ瘉鏈嶅姟
 */
export const authApiService = {
  /**
   * 鐢ㄦ埛鐧诲綍
   */
  async login(credentials: { username: string; password: string }): Promise<{
    user: User
    token: string
    refreshToken: string
  }> {
    const response = await apiClient.post<{
      access_token: string
      refresh_token: string
      token_type: string
      expires_in?: number
      user_id: string
      username: string
      role: string
      email: string
      real_name?: string
      two_factor_enabled?: boolean
    }>('/api/auth/login', credentials)

    // 鏋勯€犵敤鎴峰璞?
    const user: User = {
      id: response.user_id,
      username: response.username,
      email: response.email,
      role: response.role,
      realName: response.real_name || '',
      twoFactorEnabled: response.two_factor_enabled || false,
      permissions: [],
      avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${response.username}`,
      isActive: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }

    return {
      user,
      token: response.access_token,
      refreshToken: response.refresh_token
    }
  },

  /**
   * 鐢ㄦ埛娉ㄥ唽
   */
  async register(userData: {
    username: string
    email: string
    password: string
    first_name?: string
    last_name?: string
  }): Promise<User> {
    const response = await apiClient.post<{
      message: string
      user_id: string
      username: string
    }>('/api/auth/register', userData)
    
    return {
      id: response.user_id,
      username: response.username,
      email: userData.email,
      role: 'viewer',
      realName: userData.first_name || '',
      permissions: [],
      avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${response.username}`,
      isActive: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
  },

  /**
   * 鍒锋柊token
   */
  async refreshToken(refreshToken: string): Promise<{
    token: string
    refreshToken: string
  }> {
    const response = await apiClient.post<{
      access_token: string
      refresh_token: string
    }>('/api/auth/refresh', { refresh_token: refreshToken })

    return {
      token: response.access_token,
      refreshToken: response.refresh_token
    }
  },

  /**
   * 鐢ㄦ埛鐧诲嚭
   */
  async logout(): Promise<void> {
    await apiClient.post('/api/auth/logout')
  },

  /**
   * 鑾峰彇褰撳墠鐢ㄦ埛淇℃伅
   */
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<{
      success: boolean
      data: {
        id: string
        username: string
        email: string
        role: string
        is_active: boolean
        created_at: string
        updated_at: string
        settings?: any
        roles?: any[]
        permissions?: string[]
      }
    }>('/api/auth/profile')
    
    if (!response.success) {
      throw new Error('鑾峰彇鐢ㄦ埛淇℃伅澶辫触')
    }
    
    const userData = response.data
    return {
      id: userData.id,
      username: userData.username,
      email: userData.email,
      role: userData.role,
      realName: userData.username,
      isActive: userData.is_active,
      permissions: userData.permissions || [],
      avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${userData.username}`,
      createdAt: userData.created_at,
      updatedAt: userData.updated_at,
      settings: userData.settings || {},
      roles: userData.roles || []
    }
  },

  /**
   * 鏇存柊鐢ㄦ埛璧勬枡
   */
  async updateProfile(updates: Partial<User>): Promise<User> {
    const currentUser = JSON.parse(localStorage.getItem('auth-user') || '{}')
    if (!currentUser.id) {
      throw new Error('用户未登录')
    }
    
    // 杞崲涓哄悗绔湡鏈涚殑鏍煎紡
    const updateData: any = {}
    if (updates.username) updateData.username = updates.username
    if (updates.email) updateData.email = updates.email
    if (updates.role) updateData.role = updates.role
    if (updates.isActive !== undefined) updateData.is_active = updates.isActive
    
    await apiClient.put(`/api/auth/users/${currentUser.id}`, updateData)
    
    // 閲嶆柊鑾峰彇鐢ㄦ埛淇℃伅
    return this.getCurrentUser()
  },

  /**
   * 淇敼瀵嗙爜
   */
  async changePassword(data: {
    old_password: string
    new_password: string
  }): Promise<void> {
    await apiClient.post('/api/auth/change-password', data)
  }
}

/**
 * 浠〃鏉挎湇鍔?
 */
export const dashboardService = {
  /**
   * 鑾峰彇浠〃鏉挎暟鎹?
   */
  async getDashboardData(): Promise<DashboardStats> {
    const response = await apiClient.get<{
      success: boolean
      data: DashboardStats
    }>('/api/dashboard')
    
    if (!response.success) {
      throw new Error('获取仪表盘数据失败')
    }
    
    return response.data
  },

  /**
   * 鑾峰彇绯荤粺鐘舵€?
   */
  async getSystemStatus(): Promise<{
    status: 'healthy' | 'warning' | 'error'
    services: Array<{
      name: string
      status: 'running' | 'stopped' | 'error'
      uptime: number
      lastCheck: string
    }>
    resources: {
      cpu: number
      memory: number
      disk: number
      network: number
    }
  }> {
    return apiClient.get('/api/dashboard/system-status')
  },

  /**
   * 鑾峰彇娴嬭瘯缁熻
   */
  async getTestStats(timeRange?: string): Promise<{
    totalTests: number
    passedTests: number
    failedTests: number
    runningTests: number
    passRate: number
    trends: Array<{
      date: string
      passed: number
      failed: number
      total: number
    }>
  }> {
    const params = timeRange ? { time_range: timeRange } : {}
    const url = params ? `/api/dashboard/test-stats?time_range=${params.time_range}` : '/api/dashboard/test-stats'
    return apiClient.get(url)
  },

  /**
   * 鑾峰彇鎬ц兘鎸囨爣
   */
  async getPerformanceMetrics(): Promise<{
    averageResponseTime: number
    throughput: number
    errorRate: number
    availability: number
    trends: Array<{
      timestamp: string
      responseTime: number
      throughput: number
      errorRate: number
    }>
  }> {
    return apiClient.get('/api/dashboard/performance-metrics')
  }
}

/**
 * 椤圭洰鏈嶅姟
 */
export const projectService = {
  /**
   * 鑾峰彇椤圭洰鍒楄〃
   */
  async getProjects(params?: {
    page?: number
    pageSize?: number
    search?: string
    status?: string
    sortBy?: string
    sortOrder?: 'asc' | 'desc'
  }): Promise<PaginatedResponse<Project>> {
    const queryString = params ? '?' + new URLSearchParams(params as any).toString() : ''
    return apiClient.get<PaginatedResponse<Project>>(`/api/projects${queryString}`)
  },

  /**
   * 鑾峰彇椤圭洰璇︽儏
   */
  async getProject(id: string): Promise<Project> {
    return apiClient.get<Project>(`/api/projects/${id}`)
  },

  /**
   * 鍒涘缓椤圭洰
   */
  async createProject(projectData: Omit<Project, 'id' | 'createdAt' | 'updatedAt'>): Promise<Project> {
    return apiClient.post<Project>('/api/projects', projectData)
  },

  /**
   * 鏇存柊椤圭洰
   */
  async updateProject(id: string, updates: Partial<Project>): Promise<Project> {
    return apiClient.put<Project>(`/api/projects/${id}`, updates)
  },

  /**
   * 鍒犻櫎椤圭洰
   */
  async deleteProject(id: string): Promise<void> {
    await apiClient.delete(`/api/projects/${id}`)
  },

  /**
   * 鑾峰彇椤圭洰鎴愬憳
   */
  async getProjectMembers(projectId: string): Promise<Array<{
    user: User
    role: string
    joinedAt: string
    permissions: string[]
  }>> {
    return apiClient.get(`/api/projects/${projectId}/members`)
  },

  /**
   * 娣诲姞椤圭洰鎴愬憳
   */
  async addProjectMember(projectId: string, data: {
    userId: string
    role: string
    permissions?: string[]
  }): Promise<void> {
    await apiClient.post(`/api/projects/${projectId}/members`, data)
  },

  /**
   * 绉婚櫎椤圭洰鎴愬憳
   */
  async removeProjectMember(projectId: string, userId: string): Promise<void> {
    await apiClient.delete(`/api/projects/${projectId}/members/${userId}`)
  }
}

/**
 * 闇€姹傛湇鍔?
 */
export const requirementService = {
  /**
   * 鑾峰彇闇€姹傚垪琛?
   */
  async getRequirements(params?: {
    projectId?: string
    page?: number
    pageSize?: number
    search?: string
    status?: string
    priority?: string
  }): Promise<PaginatedResponse<any>> {
    const queryString = params ? '?' + new URLSearchParams(params as any).toString() : ''
    return apiClient.get(`/api/requirements${queryString}`)
  },

  /**
   * 鑾峰彇闇€姹傝鎯?
   */
  async getRequirement(id: string): Promise<any> {
    return apiClient.get(`/api/requirements/${id}`)
  },

  /**
   * 鍒涘缓闇€姹?
   */
  async createRequirement(data: any): Promise<any> {
    return apiClient.post('/api/requirements', data)
  },

  /**
   * 鏇存柊闇€姹?
   */
  async updateRequirement(id: string, updates: any): Promise<any> {
    return apiClient.put(`/api/requirements/${id}`, updates)
  },

  /**
   * 鍒犻櫎闇€姹?
   */
  async deleteRequirement(id: string): Promise<void> {
    await apiClient.delete(`/api/requirements/${id}`)
  }
}

/**
 * 娴嬭瘯鐢ㄤ緥鏈嶅姟
 */
export const testCaseService = {
  /**
   * 鑾峰彇娴嬭瘯鐢ㄤ緥鍒楄〃
   */
  async getTestCases(params?: {
    projectId?: string
    page?: number
    pageSize?: number
    search?: string
    status?: string
    priority?: string
    tags?: string[]
  }): Promise<PaginatedResponse<TestCase>> {
    if (!params) {
      return apiClient.get<PaginatedResponse<TestCase>>('/api/test-cases')
    }

    const searchParams = new URLSearchParams()
    
    // 澶勭悊鏅€氬弬鏁?
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && key !== 'tags') {
        searchParams.append(key, String(value))
      }
    })
    
    // 鐗规畩澶勭悊鏁扮粍鍙傛暟锛堝tags锛?
    if (params.tags && Array.isArray(params.tags)) {
      params.tags.forEach(tag => {
        searchParams.append('tags', tag)
      })
    }
    
    const queryString = searchParams.toString()
    return apiClient.get<PaginatedResponse<TestCase>>(`/api/test-cases${queryString ? '?' + queryString : ''}`)
  },

  /**
   * 鑾峰彇娴嬭瘯鐢ㄤ緥璇︽儏
   */
  async getTestCase(id: string): Promise<TestCase> {
    return apiClient.get<TestCase>(`/api/test-cases/${id}`)
  },

  /**
   * 鍒涘缓娴嬭瘯鐢ㄤ緥
   */
  async createTestCase(testCaseData: Omit<TestCase, 'id' | 'createdAt' | 'updatedAt'>): Promise<TestCase> {
    return apiClient.post<TestCase>('/api/test-cases', testCaseData)
  },

  /**
   * 鏇存柊娴嬭瘯鐢ㄤ緥
   */
  async updateTestCase(id: string, updates: Partial<TestCase>): Promise<TestCase> {
    return apiClient.put<TestCase>(`/api/test-cases/${id}`, updates)
  },

  /**
   * 鍒犻櫎娴嬭瘯鐢ㄤ緥
   */
  async deleteTestCase(id: string): Promise<void> {
    await apiClient.delete(`/api/test-cases/${id}`)
  },

  /**
   * 鎵归噺鎿嶄綔娴嬭瘯鐢ㄤ緥
   */
  async bulkOperateTestCases(operation: string, testCaseIds: string[], data?: any): Promise<{
    success: number
    failed: number
    errors: Array<{ id: string; error: string }>
  }> {
    return apiClient.post('/api/test-cases/bulk', {
      operation,
      test_case_ids: testCaseIds,
      data
    })
  },

  /**
   * 鎵ц娴嬭瘯鐢ㄤ緥
   */
  async executeTestCase(id: string, config?: any): Promise<{
    executionId: string
    status: 'queued' | 'running' | 'completed' | 'failed'
  }> {
    return apiClient.post(`/api/test-cases/${id}/execute`, config)
  },

  /**
   * 鑾峰彇娴嬭瘯鐢ㄤ緥鎵ц鍘嗗彶
   */
  async getTestCaseHistory(id: string, params?: {
    page?: number
    pageSize?: number
  }): Promise<PaginatedResponse<TestResult>> {
    return apiClient.get(`/api/test-cases/${id}/history`, { params })
  }
}

/**
 * 娴嬭瘯缁撴灉鏈嶅姟
 */
export const testResultService = {
  /**
   * 鑾峰彇娴嬭瘯缁撴灉鍒楄〃
   */
  async getTestResults(params?: {
    projectId?: string
    testCaseId?: string
    page?: number
    pageSize?: number
    status?: string
    dateRange?: [string, string]
  }): Promise<PaginatedResponse<TestResult>> {
    return apiClient.get<PaginatedResponse<TestResult>>('/api/test-results', { params })
  },

  /**
   * 鑾峰彇娴嬭瘯缁撴灉璇︽儏
   */
  async getTestResult(id: string): Promise<TestResult> {
    return apiClient.get<TestResult>(`/api/test-results/${id}`)
  },

  /**
   * 鑾峰彇娴嬭瘯鎶ュ憡
   */
  async getTestReport(id: string, format?: 'html' | 'pdf' | 'json'): Promise<any> {
    return apiClient.get(`/api/test-results/${id}/report`, {
      params: { format },
      responseType: format === 'pdf' ? 'blob' : 'json'
    })
  },

  /**
   * 瀵煎嚭娴嬭瘯缁撴灉
   */
  async exportTestResults(params: {
    format: 'csv' | 'excel' | 'pdf'
    filters?: any
    columns?: string[]
  }): Promise<Blob> {
    return apiClient.post('/api/test-results/export', params, {
      responseType: 'blob'
    })
  }
}

/**
 * 鎬ц兘娴嬭瘯鏈嶅姟
 */
export const performanceService = {
  /**
   * 鑾峰彇鎬ц兘娴嬭瘯鍒楄〃
   */
  async getPerformanceTests(params?: {
    page?: number
    pageSize?: number
    search?: string
    status?: string
  }): Promise<PaginatedResponse<PerformanceTest>> {
    return apiClient.get<PaginatedResponse<PerformanceTest>>('/api/performance', { params })
  },

  /**
   * 鍒涘缓鎬ц兘娴嬭瘯
   */
  async createPerformanceTest(testData: Omit<PerformanceTest, 'id' | 'createdAt' | 'updatedAt'>): Promise<PerformanceTest> {
    return apiClient.post<PerformanceTest>('/api/performance', testData)
  },

  /**
   * 杩愯鎬ц兘娴嬭瘯
   */
  async runPerformanceTest(id: string): Promise<{
    executionId: string
    status: 'queued' | 'running'
  }> {
    return apiClient.post(`/api/performance/${id}/run`)
  },

  /**
   * 鑾峰彇鎬ц兘娴嬭瘯缁撴灉
   */
  async getPerformanceTestResults(id: string): Promise<any> {
    return apiClient.get(`/api/performance/${id}/results`)
  },

  /**
   * 鍋滄鎬ц兘娴嬭瘯
   */
  async stopPerformanceTest(id: string): Promise<void> {
    await apiClient.post(`/api/performance/${id}/stop`)
  }
}

/**
 * 瀹夊叏娴嬭瘯鏈嶅姟
 */
export const securityService = {
  /**
   * 鑾峰彇瀹夊叏鎵弿鍒楄〃
   */
  async getSecurityScans(params?: {
    page?: number
    pageSize?: number
    search?: string
    status?: string
    scanType?: string
  }): Promise<PaginatedResponse<SecurityScan>> {
    return apiClient.get<PaginatedResponse<SecurityScan>>('/api/security', { params })
  },

  /**
   * 鍒涘缓瀹夊叏鎵弿
   */
  async createSecurityScan(scanData: Omit<SecurityScan, 'id' | 'createdAt' | 'completedAt'>): Promise<SecurityScan> {
    return apiClient.post<SecurityScan>('/api/security/scan', scanData)
  },

  /**
   * 鑾峰彇瀹夊叏鎵弿缁撴灉
   */
  async getSecurityScanResults(id: string): Promise<SecurityScan> {
    return apiClient.get<SecurityScan>(`/api/security/${id}`)
  },

  /**
   * 鍋滄瀹夊叏鎵弿
   */
  async stopSecurityScan(id: string): Promise<void> {
    await apiClient.post(`/api/security/${id}/stop`)
  }
}

/**
 * AI鏈嶅姟
 */
export const aiService = {
  /**
   * 鑾峰彇AI鍒嗘瀽鍒楄〃
   */
  async getAIAnalyses(params?: {
    page?: number
    pageSize?: number
    type?: string
    status?: string
  }): Promise<PaginatedResponse<AIAnalysis>> {
    return apiClient.get<PaginatedResponse<AIAnalysis>>('/api/ai', { params })
  },

  /**
   * 鍒涘缓AI鍒嗘瀽浠诲姟
   */
  async createAIAnalysis(data: {
    type: 'test_generation' | 'bug_analysis' | 'performance_analysis'
    input: any
    config?: any
  }): Promise<AIAnalysis> {
    return apiClient.post<AIAnalysis>('/api/ai/analyze', data)
  },

  /**
   * 鑾峰彇AI鍒嗘瀽缁撴灉
   */
  async getAIAnalysisResult(id: string): Promise<AIAnalysis> {
    return apiClient.get<AIAnalysis>(`/api/ai/${id}`)
  },

  /**
   * AI鑱婂ぉ
   */
  async chatWithAI(data: {
    message: string
    context?: any
    sessionId?: string
  }): Promise<{
    response: string
    sessionId: string
    suggestions?: string[]
  }> {
    return apiClient.post('/api/ai/chat', data)
  },

  /**
   * 鑾峰彇AI寤鸿
   */
  async getAISuggestions(data: {
    type: 'test_case' | 'bug_fix' | 'optimization'
    context: any
  }): Promise<{
    suggestions: Array<{
      title: string
      description: string
      confidence: number
      action?: string
    }>
  }> {
    return apiClient.post('/api/ai/suggestions', data)
  }
}

/**
 * 绯荤粺鏈嶅姟
 */
export const systemService = {
  /**
   * 鑾峰彇绯荤粺閰嶇疆
   */
  async getSystemConfigs(category?: string): Promise<SystemConfig[]> {
    const params = category ? { category } : {}
    return apiClient.get<SystemConfig[]>('/api/system/config', { params })
  },

  /**
   * 鏇存柊绯荤粺閰嶇疆
   */
  async updateSystemConfig(key: string, value: any): Promise<SystemConfig> {
    return apiClient.put<SystemConfig>(`/api/system/config/${key}`, { value })
  },

  /**
   * 鑾峰彇绯荤粺鏃ュ織
   */
  async getSystemLogs(params?: {
    level?: string
    startDate?: string
    endDate?: string
    page?: number
    pageSize?: number
  }): Promise<PaginatedResponse<any>> {
    return apiClient.get('/api/system/logs', { params })
  },

  /**
   * 鑾峰彇绯荤粺鍋ュ悍妫€鏌?
   */
  async getHealthCheck(): Promise<{
    status: 'healthy' | 'unhealthy'
    checks: Array<{
      name: string
      status: 'pass' | 'fail'
      message?: string
      duration: number
    }>
    timestamp: string
  }> {
    return apiClient.get('/api/health')
  }
}

/**
 * 閫氱煡鏈嶅姟
 */
export const notificationService = {
  /**
   * 鑾峰彇閫氱煡鍒楄〃
   */
  async getNotifications(params?: {
    page?: number
    pageSize?: number
    read?: boolean
    type?: string
  }): Promise<PaginatedResponse<Notification>> {
    return apiClient.get<PaginatedResponse<Notification>>('/api/notifications', { params })
  },

  /**
   * 鏍囪閫氱煡涓哄凡璇?
   */
  async markNotificationAsRead(id: string): Promise<void> {
    await apiClient.put(`/api/notifications/${id}/read`)
  },

  /**
   * 鎵归噺鏍囪閫氱煡涓哄凡璇?
   */
  async markNotificationsAsRead(ids: string[]): Promise<void> {
    await apiClient.put('/api/notifications/read', { ids })
  },

  /**
   * 鍒犻櫎閫氱煡
   */
  async deleteNotification(id: string): Promise<void> {
    await apiClient.delete(`/api/notifications/${id}`)
  },

  /**
   * 鑾峰彇鏈閫氱煡鏁伴噺
   */
  async getUnreadCount(): Promise<{ count: number }> {
    return apiClient.get('/api/notifications/unread-count')
  }
}

/**
 * 鏂囦欢鏈嶅姟
 */
export const fileService = {
  /**
   * 涓婁紶鏂囦欢
   */
  async uploadFile(file: File, options?: {
    onProgress?: (progress: number) => void
    category?: string
    metadata?: Record<string, any>
  }): Promise<{
    id: string
    url: string
    filename: string
    size: number
    type: string
  }> {
    return apiClient.upload('/api/files/upload', file, {
      fieldName: 'file',
      additionalData: {
        category: options?.category || 'general',
        metadata: options?.metadata ? JSON.stringify(options.metadata) : '{}'
      },
      onProgress: options?.onProgress
    })
  },

  /**
   * 涓嬭浇鏂囦欢
   */
  async downloadFile(id: string, filename?: string): Promise<void> {
    await apiClient.download(`/api/files/${id}/download`, filename)
  },

  /**
   * 鍒犻櫎鏂囦欢
   */
  async deleteFile(id: string): Promise<void> {
    await apiClient.delete(`/api/files/${id}`)
  },

  /**
   * 鑾峰彇鏂囦欢淇℃伅
   */
  async getFileInfo(id: string): Promise<{
    id: string
    filename: string
    size: number
    type: string
    url: string
    uploadedAt: string
    uploadedBy: string
  }> {
    return apiClient.get(`/api/files/${id}`)
  }
}

/**
 * Lighthouse鏈嶅姟
 */
export const lighthouseService = {
  /**
   * 鑾峰彇Lighthouse娴嬭瘯鍒楄〃
   */
  async getLighthouseTests(params?: {
    page?: number
    pageSize?: number
    search?: string
    status?: string
  }): Promise<PaginatedResponse<any>> {
    return apiClient.get<PaginatedResponse<any>>('/api/lighthouse', { params })
  },

  /**
   * 鍒涘缓Lighthouse娴嬭瘯
   */
  async createLighthouseTest(testData: {
    name: string
    url: string
    config?: any
  }): Promise<any> {
    return apiClient.post('/api/lighthouse', testData)
  },

  /**
   * 杩愯Lighthouse娴嬭瘯
   */
  async runLighthouseTest(id: string): Promise<{
    executionId: string
    status: 'queued' | 'running'
  }> {
    return apiClient.post(`/api/lighthouse/${id}/run`)
  },

  /**
   * 鑾峰彇Lighthouse娴嬭瘯缁撴灉
   */
  async getLighthouseTestResults(id: string): Promise<any> {
    return apiClient.get(`/api/lighthouse/${id}/results`)
  }
}

/**
 * Allure鏈嶅姟
 */
export const allureService = {
  /**
   * 鑾峰彇Allure鎶ュ憡鍒楄〃
   */
  async getAllureReports(params?: {
    page?: number
    pageSize?: number
    search?: string
  }): Promise<PaginatedResponse<any>> {
    return apiClient.get<PaginatedResponse<any>>('/api/allure', { params })
  },

  /**
   * 瀵煎叆Allure鎶ュ憡
   */
  async importAllureReport(file: File): Promise<any> {
    return apiClient.upload('/api/allure/import', file, {
      fieldName: 'report_file'
    })
  },

  /**
   * 鑾峰彇Allure鎶ュ憡璇︽儏
   */
  async getAllureReportDetails(id: string): Promise<any> {
    return apiClient.get(`/api/allure/${id}`)
  },

  /**
   * 鍒犻櫎Allure鎶ュ憡
   */
  async deleteAllureReport(id: string): Promise<void> {
    await apiClient.delete(`/api/allure/${id}`)
  }
}

/**
 * 浼氳鏈嶅姟
 */
export const meetingService = {
  /**
   * 鑾峰彇浼氳鍒楄〃
   */
  async getMeetings(params?: {
    page?: number
    pageSize?: number
    status?: string
    dateRange?: [string, string]
  }): Promise<PaginatedResponse<any>> {
    return apiClient.get<PaginatedResponse<any>>('/api/meetings', { params })
  },

  /**
   * 鍒涘缓浼氳
   */
  async createMeeting(meetingData: {
    title: string
    description?: string
    startTime: string
    duration: number
    participants: string[]
  }): Promise<any> {
    return apiClient.post('/api/meetings', meetingData)
  },

  /**
   * 鍔犲叆浼氳
   */
  async joinMeeting(id: string): Promise<{
    meetingUrl: string
    accessToken?: string
  }> {
    return apiClient.post(`/api/meetings/${id}/join`)
  },

  /**
   * 缁撴潫浼氳
   */
  async endMeeting(id: string): Promise<void> {
    await apiClient.post(`/api/meetings/${id}/end`)
  },

  /**
   * 鑾峰彇浼氳褰曞埗
   */
  async getMeetingRecordings(id: string): Promise<Array<{
    id: string
    url: string
    duration: number
    createdAt: string
  }>> {
    return apiClient.get(`/api/meetings/${id}/recordings`)
  }
}

/**
 * 瀵煎叆鏈嶅姟
 */
export const importService = {
  /**
   * 瀵煎叆娴嬭瘯鎶ュ憡
   */
  async importTestReport(file: File, format: 'allure' | 'junit' | 'testng'): Promise<{
    importId: string
    status: 'processing' | 'completed' | 'failed'
    summary?: {
      totalTests: number
      passedTests: number
      failedTests: number
    }
  }> {
    return apiClient.upload('/api/import/test-report', file, {
      fieldName: 'report_file',
      additionalData: { format }
    })
  },

  /**
   * 鑾峰彇瀵煎叆鐘舵€?
   */
  async getImportStatus(importId: string): Promise<{
    id: string
    status: 'processing' | 'completed' | 'failed'
    progress: number
    error?: string
    result?: any
  }> {
    return apiClient.get(`/api/import/${importId}/status`)
  },

  /**
   * 瀵煎叆娴嬭瘯鐢ㄤ緥
   */
  async importTestCases(file: File, format: 'csv' | 'excel'): Promise<{
    importId: string
    status: 'processing'
  }> {
    return apiClient.upload('/api/import/test-cases', file, {
      fieldName: 'file',
      additionalData: { format }
    })
  }
}

/**
 * 鐗堟湰鏈嶅姟
 */
export const versionService = {
  /**
   * 鑾峰彇鐗堟湰淇℃伅
   */
  async getVersionInfo(): Promise<{
    version: string
    buildDate: string
    gitCommit: string
    environment: string
  }> {
    return apiClient.get('/api/versions')
  },

  /**
   * 妫€鏌ユ洿鏂?
   */
  async checkForUpdates(): Promise<{
    hasUpdate: boolean
    latestVersion?: string
    releaseNotes?: string
  }> {
    return apiClient.get('/api/versions/check-updates')
  }
}

/**
 * 宸ュ叿鏈嶅姟
 */
export const toolsService = {
  /**
   * 鑾峰彇宸ュ叿閰嶇疆
   */
  async getToolsConfig(): Promise<{
    jmeter: { version: string; installed: boolean }
    sqlmap: { version: string; installed: boolean }
    lighthouse: { version: string; installed: boolean }
    allure: { version: string; installed: boolean }
  }> {
    return apiClient.get('/api/tools')
  },

  /**
   * 瀹夎宸ュ叿
   */
  async installTool(toolName: string): Promise<{
    status: 'installing' | 'completed' | 'failed'
    message: string
  }> {
    return apiClient.post(`/api/tools/${toolName}/install`)
  },

  /**
   * 鏇存柊宸ュ叿
   */
  async updateTool(toolName: string): Promise<{
    status: 'updating' | 'completed' | 'failed'
    message: string
  }> {
    return apiClient.post(`/api/tools/${toolName}/update`)
  }
}

/**
 * 璁剧疆鏈嶅姟
 */
export const settingsService = {
  /**
   * 鑾峰彇绯荤粺璁剧疆
   */
  async getSettings(category?: string): Promise<Record<string, any>> {
    const params = category ? { category } : {}
    return apiClient.get('/api/settings', { params })
  },

  /**
   * 鏇存柊绯荤粺璁剧疆
   */
  async updateSettings(settings: Record<string, any>): Promise<void> {
    await apiClient.put('/api/settings', settings)
  },

  /**
   * 閲嶇疆璁剧疆
   */
  async resetSettings(category?: string): Promise<void> {
    const params = category ? { category } : {}
    await apiClient.post('/api/settings/reset', params)
  }
}

/**
 * 瀵煎嚭鎵€鏈夋湇鍔?
 */
export const apiServices = {
  auth: authApiService,
  dashboard: dashboardService,
  project: projectService,
  requirement: requirementService,
  testCase: testCaseService,
  testResult: testResultService,
  performance: performanceService,
  security: securityService,
  ai: aiService,
  system: systemService,
  notification: notificationService,
  file: fileService,
  lighthouse: lighthouseService,
  allure: allureService,
  meeting: meetingService,
  import: importService,
  version: versionService,
  tools: toolsService,
  settings: settingsService
}

export default apiServices
