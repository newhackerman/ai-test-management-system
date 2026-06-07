// 应用常量定义

// 应用信息
export const APP_INFO = {
  NAME: 'AI自动化测试管理系统',
  VERSION: '1.0.0',
  DESCRIPTION: '基于Python+FastAPI+Playwright+Allure+JMeter+AI实现的企业级自动化测试管理平台',
  AUTHOR: 'AI Test Team',
} as const

// API端点
export const API_ENDPOINTS = {
  // 认证相关
  AUTH: {
    LOGIN: '/api/auth/login',
    LOGOUT: '/api/auth/logout',
    REFRESH: '/api/auth/refresh',
    PROFILE: '/api/auth/profile',
    CHANGE_PASSWORD: '/api/auth/change-password',
  },
  
  // 仪表板
  DASHBOARD: {
    STATS: '/api/dashboard/stats',
    CHARTS: '/api/dashboard/charts',
    RECENT_ACTIVITIES: '/api/dashboard/activities',
  },
  
  // 项目管理
  PROJECTS: {
    LIST: '/api/projects',
    CREATE: '/api/projects',
    DETAIL: (id: string) => `/api/projects/${id}`,
    UPDATE: (id: string) => `/api/projects/${id}`,
    DELETE: (id: string) => `/api/projects/${id}`,
    MEMBERS: (id: string) => `/api/projects/${id}/members`,
  },
  
  // 需求管理
  REQUIREMENTS: {
    LIST: '/api/requirements',
    CREATE: '/api/requirements',
    DETAIL: (id: string) => `/api/requirements/${id}`,
    UPDATE: (id: string) => `/api/requirements/${id}`,
    DELETE: (id: string) => `/api/requirements/${id}`,
  },
  
  // 测试用例
  TEST_CASES: {
    LIST: '/api/test-cases',
    CREATE: '/api/test-cases',
    DETAIL: (id: string) => `/api/test-cases/${id}`,
    UPDATE: (id: string) => `/api/test-cases/${id}`,
    DELETE: (id: string) => `/api/test-cases/${id}`,
    EXECUTE: (id: string) => `/api/test-cases/${id}/execute`,
  },
  
  // 测试结果
  TEST_RESULTS: {
    LIST: '/api/test-results',
    DETAIL: (id: string) => `/api/test-results/${id}`,
    EXPORT: '/api/test-results/export',
  },
  
  // 性能测试
  PERFORMANCE: {
    TESTS: '/api/performance/tests',
    RUN: '/api/performance/run',
    RESULTS: '/api/performance/results',
    REPORTS: '/api/performance/reports',
  },
  
  // 安全测试
  SECURITY: {
    SCANS: '/api/security/scans',
    RUN: '/api/security/scan',
    RESULTS: '/api/security/results',
    VULNERABILITIES: '/api/security/vulnerabilities',
  },
  
  // AI服务
  AI: {
    ANALYZE: '/api/ai/analyze',
    GENERATE: '/api/ai/generate',
    CHAT: '/api/ai/chat',
    SUGGESTIONS: '/api/ai/suggestions',
  },
  
  // Lighthouse
  LIGHTHOUSE: {
    AUDITS: '/api/lighthouse/audits',
    RUN: '/api/lighthouse/run',
    REPORTS: '/api/lighthouse/reports',
  },
  
  // Allure报告
  ALLURE: {
    REPORTS: '/api/allure/reports',
    IMPORT: '/api/allure/import',
    GENERATE: '/api/allure/generate',
  },
  
  // 视频会议
  MEETINGS: {
    LIST: '/api/meetings',
    CREATE: '/api/meetings',
    JOIN: (id: string) => `/api/meetings/${id}/join`,
    RECORDINGS: '/api/meetings/recordings',
  },
  
  // 系统优化
  SYSTEM: {
    STATUS: '/api/system/status',
    METRICS: '/api/system/metrics',
    OPTIMIZE: '/api/system/optimize',
    LOGS: '/api/system/logs',
  },
  
  // 配置管理
  CONFIG: {
    LIST: '/api/config',
    UPDATE: '/api/config',
    RELOAD: '/api/config/reload',
    BACKUP: '/api/config/backup',
    RESTORE: '/api/config/restore',
  },
  
  // 文件上传
  UPLOAD: {
    FILE: '/api/upload/file',
    IMAGE: '/api/upload/image',
    DOCUMENT: '/api/upload/document',
  },
  
  // 用户管理
  USERS: {
    LIST: '/api/users',
    CREATE: '/api/users',
    DETAIL: (id: string) => `/api/users/${id}`,
    UPDATE: (id: string) => `/api/users/${id}`,
    DELETE: (id: string) => `/api/users/${id}`,
  },
  
  // 报告导入
  IMPORT: {
    REPORT: '/api/import/report',
    STATUS: (id: string) => `/api/import/status/${id}`,
  },
} as const

// 本地存储键名
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth-token',
  REFRESH_TOKEN: 'refresh-token',
  USER_PROFILE: 'user-profile',
  THEME: 'ui-theme',
  LANGUAGE: 'app-language',
  SIDEBAR_COLLAPSED: 'sidebar-collapsed',
  DASHBOARD_LAYOUT: 'dashboard-layout',
  TABLE_SETTINGS: 'table-settings',
  FORM_DRAFTS: 'form-drafts',
  RECENT_SEARCHES: 'recent-searches',
  USER_PREFERENCES: 'user-preferences',
} as const

// 主题相关
export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
  SYSTEM: 'system',
} as const

// 语言选项
export const LANGUAGES = {
  ZH_CN: 'zh-CN',
  EN_US: 'en-US',
} as const

// 分页配置
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
  MAX_PAGE_SIZE: 1000,
} as const

// 文件上传配置
export const UPLOAD = {
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_IMAGE_TYPES: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
  ALLOWED_DOCUMENT_TYPES: [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'text/csv',
  ],
  CHUNK_SIZE: 1024 * 1024, // 1MB chunks for large files
} as const

// 表单验证规则
export const VALIDATION = {
  PASSWORD: {
    MIN_LENGTH: 8,
    MAX_LENGTH: 128,
    REQUIRE_UPPERCASE: true,
    REQUIRE_LOWERCASE: true,
    REQUIRE_NUMBERS: true,
    REQUIRE_SPECIAL_CHARS: true,
  },
  EMAIL: {
    PATTERN: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  },
  PHONE: {
    PATTERN: /^1[3-9]\d{9}$/, // 中国手机号
  },
  USERNAME: {
    MIN_LENGTH: 3,
    MAX_LENGTH: 32,
    PATTERN: /^[a-zA-Z0-9_-]+$/,
  },
} as const

// 状态常量
export const STATUS = {
  // 通用状态
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  PENDING: 'pending',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
  
  // 测试状态
  TEST: {
    DRAFT: 'draft',
    READY: 'ready',
    RUNNING: 'running',
    PASSED: 'passed',
    FAILED: 'failed',
    SKIPPED: 'skipped',
    BLOCKED: 'blocked',
  },
  
  // 项目状态
  PROJECT: {
    PLANNING: 'planning',
    ACTIVE: 'active',
    ON_HOLD: 'on_hold',
    COMPLETED: 'completed',
    ARCHIVED: 'archived',
  },
  
  // 用户状态
  USER: {
    ACTIVE: 'active',
    INACTIVE: 'inactive',
    SUSPENDED: 'suspended',
    PENDING_VERIFICATION: 'pending_verification',
  },
} as const

// 优先级
export const PRIORITY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const

// 严重程度
export const SEVERITY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const

// 通知类型
export const NOTIFICATION_TYPES = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
} as const

// WebSocket事件类型
export const WS_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  ERROR: 'error',
  
  // 测试相关事件
  TEST_STARTED: 'test_started',
  TEST_PROGRESS: 'test_progress',
  TEST_COMPLETED: 'test_completed',
  TEST_FAILED: 'test_failed',
  
  // 系统事件
  SYSTEM_STATUS: 'system_status',
  NOTIFICATION: 'notification',
  USER_ACTIVITY: 'user_activity',
} as const

// 错误代码
export const ERROR_CODES = {
  // 认证错误
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  
  // 验证错误
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  REQUIRED_FIELD: 'REQUIRED_FIELD',
  INVALID_FORMAT: 'INVALID_FORMAT',
  
  // 业务错误
  RESOURCE_NOT_FOUND: 'RESOURCE_NOT_FOUND',
  RESOURCE_CONFLICT: 'RESOURCE_CONFLICT',
  OPERATION_FAILED: 'OPERATION_FAILED',
  
  // 系统错误
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',
} as const

// 时间格式
export const DATE_FORMATS = {
  DATE: 'YYYY-MM-DD',
  TIME: 'HH:mm:ss',
  DATETIME: 'YYYY-MM-DD HH:mm:ss',
  DATETIME_SHORT: 'MM-DD HH:mm',
  ISO: 'YYYY-MM-DDTHH:mm:ss.SSSZ',
} as const

// 正则表达式
export const REGEX = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PHONE: /^1[3-9]\d{9}$/,
  URL: /^https?:\/\/.+/,
  IP: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
  UUID: /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
  HEX_COLOR: /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/,
  SLUG: /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
} as const

// 键盘快捷键
export const SHORTCUTS = {
  SAVE: 'Ctrl+S',
  COPY: 'Ctrl+C',
  PASTE: 'Ctrl+V',
  UNDO: 'Ctrl+Z',
  REDO: 'Ctrl+Y',
  SEARCH: 'Ctrl+F',
  NEW: 'Ctrl+N',
  REFRESH: 'F5',
  HELP: 'F1',
  TOGGLE_SIDEBAR: 'Ctrl+B',
  TOGGLE_THEME: 'Ctrl+Shift+T',
} as const

// 动画持续时间（毫秒）
export const ANIMATION_DURATION = {
  FAST: 150,
  NORMAL: 300,
  SLOW: 500,
  VERY_SLOW: 1000,
} as const

// Z-index层级
export const Z_INDEX = {
  DROPDOWN: 1000,
  STICKY: 1020,
  FIXED: 1030,
  MODAL_BACKDROP: 1040,
  MODAL: 1050,
  POPOVER: 1060,
  TOOLTIP: 1070,
  TOAST: 1080,
} as const

// 环境变量
export const ENV = {
  API_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  WS_URL: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/ws',
  APP_TITLE: import.meta.env.VITE_APP_TITLE || 'AI自动化测试管理系统',
  NODE_ENV: import.meta.env.NODE_ENV || 'development',
  DEV: import.meta.env.DEV,
  PROD: import.meta.env.PROD,
} as const