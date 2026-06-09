import React, { useState } from 'react'
import { Download, Filter, Plus, RefreshCw, Search, Upload, Users as UsersIcon } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Input } from '@/components/ui/Input'
import { Pagination } from '@/components/ui/Pagination'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { BatchOperationDialog } from '@/components/users/BatchOperationDialog'
import { CreateUserDialog } from '@/components/users/CreateUserDialog'
import { EditUserDialog } from '@/components/users/EditUserDialog'
import { ImportUsersDialog } from '@/components/users/ImportUsersDialog'
import { UserPermissionsDialog } from '@/components/users/UserPermissionsDialog'
import { UserTable } from '@/components/users/UserTable'
import { useRoles, useUserFilters, useUserImportExport, useUsers } from '@/hooks/useUsers'
import type { User } from '@/types'

const DEFAULT_RESET_PASSWORD = 'TempPass123!'

const Users: React.FC = () => {
  const { filters, updateFilter, resetFilters } = useUserFilters()
  const {
    users,
    total,
    page,
    pageSize,
    totalPages,
    isLoading,
    refetch,
    createUser,
    updateUser,
    deleteUser,
    lockUser,
    unlockUser,
    resetPassword,
    batchUpdate,
    isBatchUpdating,
  } = useUsers(filters)
  const { data: roles = [] } = useRoles()
  const { exportUsers, importUsers, isExporting, isImporting } = useUserImportExport()

  const [selectedUsers, setSelectedUsers] = useState<User[]>([])
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [viewingUserPermissions, setViewingUserPermissions] = useState<User | null>(null)
  const [deletingUser, setDeletingUser] = useState<User | null>(null)
  const [lockingUser, setLockingUser] = useState<User | null>(null)
  const [resettingPasswordUser, setResettingPasswordUser] = useState<User | null>(null)
  const [showBatchDialog, setShowBatchDialog] = useState(false)
  const [showImportDialog, setShowImportDialog] = useState(false)

  const handleSelectUser = (user: User, selected: boolean) => {
    setSelectedUsers((prev) => (selected ? [...prev.filter((item) => item.id !== user.id), user] : prev.filter((item) => item.id !== user.id)))
  }

  const handleSelectAll = (selected: boolean) => {
    setSelectedUsers((prev) => {
      const currentPageIds = new Set(users.map((user) => user.id))
      if (!selected) return prev.filter((user) => !currentPageIds.has(user.id))
      const merged = new Map(prev.map((user) => [user.id, user]))
      users.forEach((user) => merged.set(user.id, user))
      return Array.from(merged.values())
    })
  }

  const handleDeleteUser = async (user: User) => {
    await deleteUser(String(user.id))
    setSelectedUsers((prev) => prev.filter((item) => item.id !== user.id))
    setDeletingUser(null)
  }

  const handleResetPassword = async (user: User) => {
    await resetPassword({
      userId: String(user.id),
      newPassword: DEFAULT_RESET_PASSWORD,
      forceChange: true,
    })
    setResettingPasswordUser(null)
  }

  const handleToggleLock = async (user: User) => {
    if (user.status === 'locked') {
      await unlockUser(String(user.id))
    } else {
      await lockUser({ userId: String(user.id), reason: '管理员手动锁定' })
    }
    setLockingUser(null)
  }

  const handleImport = async (file: File) => {
    await importUsers(file, {
      onSuccess: () => {
        setShowImportDialog(false)
        refetch()
      },
    })
  }

  const handleBatchOperation = async (action: string, data?: { role_id?: number; reason?: string }) => {
    const userIds = selectedUsers.map((user) => String(user.id))
    await batchUpdate({
      userIds,
      action: action as 'activate' | 'deactivate' | 'delete' | 'assign_role' | 'remove_role',
      data,
    })
    setSelectedUsers([])
    setShowBatchDialog(false)
  }

  const startIndex = total === 0 ? 0 : (page - 1) * pageSize + 1
  const endIndex = Math.min(page * pageSize, total)

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">用户管理</h1>
          <p className="text-sm text-muted-foreground">管理系统账号、角色分配、状态和导入导出，共 {total} 个用户</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" onClick={() => exportUsers(filters)} disabled={isExporting}>
            <Download className="mr-2 h-4 w-4" />
            {isExporting ? '导出中...' : '导出'}
          </Button>
          <Button variant="outline" onClick={() => setShowImportDialog(true)} disabled={isImporting}>
            <Upload className="mr-2 h-4 w-4" />
            导入
          </Button>
          {selectedUsers.length > 0 && (
            <Button variant="outline" onClick={() => setShowBatchDialog(true)}>
              <UsersIcon className="mr-2 h-4 w-4" />
              批量操作 ({selectedUsers.length})
            </Button>
          )}
          <Button variant="outline" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            新增用户
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="gap-3 p-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <CardTitle>用户列表</CardTitle>
              <CardDescription>显示 {startIndex} - {endIndex} 条，共 {total} 条记录</CardDescription>
            </div>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-[minmax(220px,1fr)_150px_170px_auto] xl:w-[720px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="搜索用户名、邮箱、昵称"
                  value={filters.search || ''}
                  onChange={(event) => updateFilter('search', event.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={filters.status || ''} onValueChange={(value) => updateFilter('status', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">全部状态</SelectItem>
                  <SelectItem value="active">启用</SelectItem>
                  <SelectItem value="locked">锁定</SelectItem>
                  <SelectItem value="disabled">禁用</SelectItem>
                  <SelectItem value="pending">待审核</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filters.role || ''} onValueChange={(value) => updateFilter('role', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="角色" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">全部角色</SelectItem>
                  {roles.map((role) => (
                    <SelectItem key={role.id} value={role.code}>
                      {role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button variant="outline" onClick={resetFilters}>
                <Filter className="mr-2 h-4 w-4" />
                重置
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <UserTable
            users={users}
            loading={isLoading}
            selectedUsers={selectedUsers}
            onSelectUser={handleSelectUser}
            onSelectAll={handleSelectAll}
            onEdit={setEditingUser}
            onDelete={setDeletingUser}
            onResetPassword={setResettingPasswordUser}
            onToggleLock={setLockingUser}
            onViewPermissions={setViewingUserPermissions}
          />

          {totalPages > 1 && (
            <div className="mt-6">
              <Pagination currentPage={page} totalPages={totalPages} onPageChange={(nextPage) => updateFilter('page', nextPage)} />
            </div>
          )}
        </CardContent>
      </Card>

      <CreateUserDialog open={showCreateDialog} onClose={() => setShowCreateDialog(false)} onCreate={createUser} />

      <EditUserDialog
        open={Boolean(editingUser)}
        user={editingUser}
        onClose={() => setEditingUser(null)}
        onUpdate={(userId, data) => updateUser({ userId, data })}
      />

      <UserPermissionsDialog open={Boolean(viewingUserPermissions)} user={viewingUserPermissions} onClose={() => setViewingUserPermissions(null)} />

      {deletingUser && (
        <ConfirmDialog
          open={Boolean(deletingUser)}
          title="删除用户"
          description={`确定要删除用户 "${deletingUser.username}" 吗？该用户会被标记为已删除。`}
          confirmText="删除"
          cancelText="取消"
          variant="destructive"
          onConfirm={() => handleDeleteUser(deletingUser)}
          onCancel={() => setDeletingUser(null)}
        />
      )}

      {lockingUser && (
        <ConfirmDialog
          open={Boolean(lockingUser)}
          title={lockingUser.status === 'locked' ? '解锁用户' : '锁定用户'}
          description={
            lockingUser.status === 'locked'
              ? `确定要解锁用户 "${lockingUser.username}" 吗？`
              : `确定要锁定用户 "${lockingUser.username}" 吗？锁定后用户将无法登录。`
          }
          confirmText={lockingUser.status === 'locked' ? '解锁' : '锁定'}
          cancelText="取消"
          variant={lockingUser.status === 'locked' ? 'default' : 'destructive'}
          onConfirm={() => handleToggleLock(lockingUser)}
          onCancel={() => setLockingUser(null)}
        />
      )}

      {resettingPasswordUser && (
        <ConfirmDialog
          open={Boolean(resettingPasswordUser)}
          title="重置密码"
          description={`确定要重置用户 "${resettingPasswordUser.username}" 的密码吗？新密码为 "${DEFAULT_RESET_PASSWORD}"。`}
          confirmText="重置"
          cancelText="取消"
          variant="destructive"
          onConfirm={() => handleResetPassword(resettingPasswordUser)}
          onCancel={() => setResettingPasswordUser(null)}
        />
      )}

      <BatchOperationDialog
        open={showBatchDialog}
        selectedUsers={selectedUsers}
        onClose={() => setShowBatchDialog(false)}
        onConfirm={handleBatchOperation}
        loading={isBatchUpdating}
      />

      <ImportUsersDialog open={showImportDialog} onClose={() => setShowImportDialog(false)} onImport={handleImport} loading={isImporting} />
    </div>
  )
}

export default Users
