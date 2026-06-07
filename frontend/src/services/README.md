# API集成和认证服务

## 概述

本模块实现了与FastAPI后端的完整API集成和认证服务，确保前端与现有后端100%兼容。

## 主要组件

### 1. API客户端 (`/lib/api-client.ts`)

- **功能**: 统一的HTTP客户端，支持请求拦截、响应处理、错误重试
- **特性**:
  - 自动添加认证头
  - 请求重试机制
  - 响应拦截和错误处理
  - 文件上传/下载支持
  - 批量请求支持

### 2. 认证服务 (`auth-service.ts`)

- **功能**: 完整的用户认证和授权管理
- **API兼容性**:
  - `POST /api/auth/login` - 用户登录
  - `POST /api/auth/logout` - 用户登出
  - `GET /api/auth/profile` - 获取用户信息
  - `POST /api/auth/refresh` - 刷新token
  - `POST /api/auth/register` - 用户注册
  - `POST /api/auth/change-password` - 修改密码
  - `GET /api/auth/permissions` - 获取用户权限

### 3. API服务层 (`api-services.ts`)

- **功能**: 封装所有业务API调用
- **服务模块**:
  - 认证服务 (`authApiService`)
  - 仪表板服务 (`dashboardService`)
  - 项目管理服务 (`projectService`)
  - 测试用例服务 (`testCaseService`)
  - 测试结果服务 (`testResultService`)
  - 性能测试服务 (`performanceService`)
  - 安全测试服务 (`securityService`)
  - AI服务 (`aiService`)
  - 系统服务 (`systemService`)
  - 其他业务服务...

### 4. 错误处理 (`/lib/api-error-handler.ts`)

- **功能**: 统一的API错误处理和用户友好的错误提示
- **特性**:
  - 错误分类和映射
  - 自动重试机制
  - 用户友好的错误消息
  - 错误日志记录

### 5. 请求拦截器 (`/lib/request-interceptors.ts`)

- **功能**: 请求和响应的拦截处理
- **拦截器类型**:
  - 认证拦截器 - 自动添加token
  - 日志拦截器 - 请求日志记录
  - 缓存拦截器 - 响应缓存
  - 重试拦截器 - 失败重试
  - 性能监控拦截器 - 性能指标收集

## 后端API兼容性

### 认证API

```typescript
// 登录请求
POST /api/auth/login
{
  "username": "string",
  "password": "string"
}

// 登录响应
{
  "access_token": "string",
  "refresh_token": "string", 
  "token_type": "Bearer",
  "expires_in": 3600,
  "user_id": "string",
  "username": "string",
  "role": "string",
  "email": "string"
}
```

### 用户信息API

```typescript
// 获取用户信息
GET /api/auth/profile
Authorization: Bearer <token>

// 响应格式
{
  "success": true,
  "data": {
    "id": "string",
    "username": "string", 
    "email": "string",
    "role": "string",
    "is_active": boolean,
    "created_at": "string",
    "updated_at": "string",
    "permissions": ["string"],
    "roles": [object]
  }
}
```

### 仪表板API

```typescript
// 获取仪表板数据
GET /api/dashboard
Authorization: Bearer <token>

// 响应格式
{
  "success": true,
  "data": {
    "totalTests": number,
    "passedTests": number,
    "failedTests": number,
    "runningTests": number,
    "totalProjects": number,
    "activeProjects": number,
    "totalUsers": number,
    "systemHealth": "healthy" | "warning" | "error"
  }
}
```

## 使用示例

### 基本认证流程

```typescript
import { authService } from '@/services/auth-service'
import { useAuthStore } from '@/stores/auth'

// 登录
const login = async (username: string, password: string) => {
  try {
    const authResponse = await authService.login({ username, password })
    console.log('登录成功:', authResponse.user)
  } catch (error) {
    console.error('登录失败:', error.message)
  }
}

// 获取当前用户
const getCurrentUser = async () => {
  try {
    const user = await authService.getCurrentUser()
    console.log('当前用户:', user)
  } catch (error) {
    console.error('获取用户信息失败:', error.message)
  }
}

// 检查权限
const checkPermission = () => {
  const hasReadPermission = authService.hasPermission('read')
  const isAdmin = authService.hasRole('admin')
  
  console.log('有读取权限:', hasReadPermission)
  console.log('是管理员:', isAdmin)
}
```

### API服务调用

```typescript
import { apiServices } from '@/services/api-services'

// 获取仪表板数据
const getDashboard = async () => {
  try {
    const dashboardData = await apiServices.dashboard.getDashboardData()
    console.log('仪表板数据:', dashboardData)
  } catch (error) {
    console.error('获取仪表板数据失败:', error.message)
  }
}

// 获取项目列表
const getProjects = async () => {
  try {
    const projects = await apiServices.project.getProjects({
      page: 1,
      pageSize: 20,
      search: 'test'
    })
    console.log('项目列表:', projects)
  } catch (error) {
    console.error('获取项目列表失败:', error.message)
  }
}
```

### 状态管理集成

```typescript
import { useAuthStore } from '@/stores/auth'

const LoginComponent = () => {
  const { login, isLoading, error, user } = useAuthStore()
  
  const handleLogin = async (credentials) => {
    try {
      await login(credentials)
      // 登录成功，用户信息已自动更新到store
    } catch (error) {
      // 错误已自动设置到store的error状态
    }
  }
  
  return (
    <div>
      {isLoading && <div>登录中...</div>}
      {error && <div>错误: {error}</div>}
      {user && <div>欢迎, {user.username}!</div>}
    </div>
  )
}
```

## 安全特性

1. **Token管理**: 自动处理access token和refresh token
2. **自动刷新**: Token即将过期时自动刷新
3. **安全存储**: 敏感信息安全存储在localStorage
4. **权限控制**: 基于角色和权限的访问控制
5. **错误处理**: 统一的错误处理和用户提示

## 测试

运行认证集成测试:

```bash
npm run test src/test/auth-integration.test.ts
```

## 配置

### 环境变量

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### API客户端配置

```typescript
const apiClient = new ApiClient({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30000,
  retries: 2
})
```

## 注意事项

1. **后端兼容性**: 所有API调用都与现有FastAPI后端完全兼容
2. **错误处理**: 统一的错误处理确保用户体验一致
3. **性能优化**: 请求缓存和去重减少不必要的API调用
4. **类型安全**: 完整的TypeScript类型定义确保类型安全
5. **可扩展性**: 模块化设计便于添加新的API服务

## 后续扩展

1. **离线支持**: 添加离线缓存和同步机制
2. **实时通信**: 集成WebSocket实时数据更新
3. **文件处理**: 增强文件上传和下载功能
4. **批量操作**: 支持更多批量API操作
5. **性能监控**: 添加API性能监控和分析