# 权限管理系统

这是一个完整的权限管理系统，基于RBAC（基于角色的访问控制）模型实现。

## 功能特性

### 1. 角色管理
- ✅ 角色CRUD操作（创建、查看、编辑、删除）
- ✅ 系统角色保护（系统角色不可编辑或删除）
- ✅ 角色状态管理（启用/禁用）
- ✅ 角色搜索和筛选
- ✅ 角色权限配置

### 2. 权限管理
- ✅ 权限CRUD操作
- ✅ 按模块分组管理
- ✅ 权限搜索和筛选
- ✅ 权限代码自动生成

### 3. 权限矩阵
- ✅ 可视化权限分配
- ✅ 角色-权限关系展示
- ✅ 矩阵数据导出
- ✅ 筛选和搜索功能

### 4. 用户体验
- ✅ 响应式设计
- ✅ 加载状态处理
- ✅ 错误处理和提示
- ✅ 确认对话框
- ✅ 分页支持

## 组件结构

```
permissions/
├── CreateRoleDialog.tsx          # 创建角色对话框
├── EditRoleDialog.tsx            # 编辑角色对话框
├── CreatePermissionDialog.tsx    # 创建权限对话框
├── EditPermissionDialog.tsx      # 编辑权限对话框
├── RolePermissionsDialog.tsx     # 角色权限配置对话框
├── PermissionMatrixView.tsx      # 权限矩阵视图
└── README.md                     # 文档
```

## Hooks

```
hooks/
├── useRoles.ts                   # 角色管理Hook
├── usePermissions.ts             # 权限管理Hook
├── usePermissionMatrix.ts        # 权限矩阵Hook
└── useAuthPermissions.ts         # 权限检查Hook
```

## API接口

```
api/
├── auth.ts                       # 认证相关API
├── role.ts                       # 角色管理API
└── permission.ts                 # 权限管理API
```

## 使用方法

### 1. 在应用中使用权限管理页面

```tsx
import Permissions from '@/pages/Permissions';

// 在路由中使用
<Route path="/permissions" component={Permissions} />
```

### 2. 权限检查

```tsx
import { useAuthPermissions } from '@/hooks/useAuthPermissions';

const MyComponent = () => {
  const { hasPermission, hasRole } = useAuthPermissions();
  
  return (
    <div>
      {hasPermission('user:create') && (
        <Button>创建用户</Button>
      )}
      
      {hasRole('admin') && (
        <AdminPanel />
      )}
    </div>
  );
};
```

### 3. 认证上下文

```tsx
import { AuthProvider } from '@/contexts/AuthContext';

// 在应用根组件中包装
<AuthProvider>
  <App />
</AuthProvider>
```

## 权限代码规范

权限代码采用 `模块:操作` 的格式：

- `user:create` - 创建用户
- `user:read` - 查看用户
- `user:update` - 更新用户
- `user:delete` - 删除用户
- `role:create` - 创建角色
- `role:edit` - 编辑角色
- `permission:assign` - 分配权限

## 系统角色

系统预定义了以下角色：

1. **Admin（系统管理员）** - 拥有所有权限
2. **项目管理员** - 项目管理相关权限
3. **需求管理人员** - 需求管理相关权限
4. **设计人员** - 设计相关权限
5. **架构师** - 架构设计权限
6. **开发人员** - 开发相关权限
7. **测试人员** - 测试管理权限
8. **运维人员** - 系统运维权限
9. **第三方人员** - 受限的查看权限

## 安全特性

- ✅ JWT令牌认证
- ✅ 权限级别访问控制
- ✅ 系统角色保护
- ✅ 操作确认机制
- ✅ 审计日志记录
- ✅ 会话管理

## 技术栈

- **前端**: React 18+ + TypeScript + Tailwind CSS
- **状态管理**: React Context + useReducer
- **UI组件**: 自定义UI组件库
- **HTTP客户端**: Axios
- **表单处理**: 原生React表单处理
- **图标**: Lucide React

## 开发指南

### 添加新权限

1. 在后端定义权限代码
2. 在前端权限检查中使用
3. 在UI中根据权限显示/隐藏功能

### 添加新角色

1. 在后端创建角色
2. 分配相应权限
3. 在前端权限检查中使用

### 自定义权限检查

```tsx
const { hasPermission, hasAnyPermission, hasAllPermissions } = useAuthPermissions();

// 检查单个权限
if (hasPermission('user:create')) {
  // 显示创建按钮
}

// 检查多个权限中的任意一个
if (hasAnyPermission(['user:create', 'user:edit'])) {
  // 显示用户操作菜单
}

// 检查是否拥有所有权限
if (hasAllPermissions(['user:create', 'user:edit', 'user:delete'])) {
  // 显示完整的用户管理界面
}
```

## 注意事项

1. 系统角色不能被编辑或删除
2. 删除角色前会检查是否有用户使用该角色
3. 权限代码一旦创建不能修改
4. 超级管理员拥有所有权限，无需单独检查
5. 权限检查在前端和后端都需要实现

## 故障排除

### 权限检查不生效
- 检查用户是否已登录
- 确认用户拥有相应角色
- 验证权限代码是否正确

### 组件无法加载
- 检查API接口是否正常
- 确认网络连接
- 查看浏览器控制台错误信息

### 权限矩阵显示异常
- 检查权限矩阵API返回数据格式
- 确认角色和权限数据完整性
- 验证组件props传递是否正确