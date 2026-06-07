# 🔧 认证问题修复指南

## 问题诊断

前端登录成功后，在获取用户数据时收到401未授权错误。

## 修复步骤

### 1. ✅ 已修复的问题

1. **Dashboard API调用问题**
   - 原问题：Dashboard直接使用fetch，没有携带认证token
   - 修复：创建了统一的API服务，自动处理认证token

2. **API客户端配置问题**
   - 原问题：baseURL配置重复包含/api/v1
   - 修复：统一baseURL配置

3. **前端环境配置**
   - 更新了.env文件中的API_BASE_URL配置

### 2. 🔍 调试工具

创建了认证调试工具 `auth-debug.ts`，可以在浏览器控制台使用：

```javascript
// 检查认证状态
debugAuth()

// 测试API调用
testApiCall()
```

### 3. 📝 测试步骤

1. **清除浏览器缓存和localStorage**
   ```javascript
   localStorage.clear()
   ```

2. **重新登录**
   - 用户名: admin
   - 密码: admin123

3. **检查认证状态**
   ```javascript
   debugAuth()
   ```

4. **测试API调用**
   ```javascript
   testApiCall()
   ```

### 4. 🚀 启动服务

1. **启动后端**
   ```bash
   .\start_backend.bat
   ```

2. **启动前端**
   ```bash
   cd frontend
   npm run dev
   ```

### 5. 🔧 如果问题仍然存在

1. **检查后端日志**
   - 查看认证中间件是否正确处理Bearer token
   - 检查JWT token是否有效

2. **检查前端网络请求**
   - 打开浏览器开发者工具
   - 查看Network标签页
   - 确认请求头包含Authorization字段

3. **验证token格式**
   ```javascript
   const authData = JSON.parse(localStorage.getItem('auth-storage'))
   console.log('Token:', authData.state.token)
   ```

### 6. 🎯 预期结果

修复后应该看到：
- ✅ 登录成功
- ✅ Dashboard正常显示用户统计数据
- ✅ 不再出现401错误
- ✅ API调用正常携带认证token

## 技术细节

### 修复的文件

1. `frontend/src/pages/Dashboard.tsx` - 使用统一API服务
2. `frontend/src/services/api-service.ts` - 新建统一API服务
3. `frontend/src/lib/api-client.ts` - 修复baseURL配置
4. `frontend/.env` - 更新API配置
5. `frontend/src/utils/auth-debug.ts` - 新建调试工具

### 认证流程

1. 用户登录 → 获取JWT token
2. Token存储在localStorage中
3. API调用时自动添加Authorization头
4. 后端验证token并返回数据

### 错误处理

- 401错误：自动清除认证状态并重定向到登录页
- 网络错误：显示友好的错误信息
- Token过期：自动处理并提示重新登录