import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Checkbox } from '@/components/ui/Checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Search, Shield, Check, X } from 'lucide-react';
import { getRolePermissions, updateRolePermissions } from '@/api/role';
import { getAllPermissions } from '@/api/permission';
import { toast } from 'sonner';
import type { Role, Permission } from '@/types';

interface RolePermissionsDialogProps {
  open: boolean;
  role: Role;
  onClose: () => void;
  onSuccess: () => void;
}

interface PermissionGroup {
  module: string;
  moduleName: string;
  permissions: Permission[];
}

const MODULE_NAMES: Record<string, string> = {
  user_management: '用户管理',
  role_management: '角色管理',
  permission_management: '权限管理',
  project_management: '项目管理',
  requirement_management: '需求管理',
  test_management: '测试管理',
  system_config: '系统配置',
  audit: '审计日志',
  monitoring: '系统监控',
  data_management: '数据管理'
};

export const RolePermissionsDialog: React.FC<RolePermissionsDialogProps> = ({
  open,
  role,
  onClose,
  onSuccess
}) => {
  const [allPermissions, setAllPermissions] = useState<Permission[]>([]);
  const [rolePermissions, setRolePermissions] = useState<number[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<number[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (open && role) {
      loadData();
    }
  }, [open, role]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [permissionsResponse, rolePermissionsResponse] = await Promise.all([
        getAllPermissions(),
        getRolePermissions(role.id)
      ]);

      if (permissionsResponse.success) {
        setAllPermissions(permissionsResponse.data);
      }

      if (rolePermissionsResponse.success) {
        const permissionIds = rolePermissionsResponse.data.map((p: any) => p.id);
        setRolePermissions(permissionIds);
        setSelectedPermissions(permissionIds);
      }
    } catch (error) {
      console.error('加载权限数据失败:', error);
      toast.error('加载权限数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateRolePermissions(role.id, selectedPermissions);
      toast.success('权限配置保存成功');
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || '保存权限配置失败');
    } finally {
      setIsSaving(false);
    }
  };

  const handlePermissionToggle = (permissionId: number, checked: boolean) => {
    if (checked) {
      setSelectedPermissions(prev => [...prev, permissionId]);
    } else {
      setSelectedPermissions(prev => prev.filter(id => id !== permissionId));
    }
  };

  const handleModuleToggle = (modulePermissions: Permission[], checked: boolean) => {
    const modulePermissionIds = modulePermissions.map(p => p.id);
    
    if (checked) {
      setSelectedPermissions(prev => [
        ...prev.filter(id => !modulePermissionIds.includes(id)),
        ...modulePermissionIds
      ]);
    } else {
      setSelectedPermissions(prev => 
        prev.filter(id => !modulePermissionIds.includes(id))
      );
    }
  };

  const getPermissionGroups = (): PermissionGroup[] => {
    const filtered = allPermissions.filter(permission =>
      permission.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      permission.code.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const groups = filtered.reduce((acc, permission) => {
      const existing = acc.find(g => g.module === permission.module);
      if (existing) {
        existing.permissions.push(permission);
      } else {
        acc.push({
          module: permission.module,
          moduleName: MODULE_NAMES[permission.module] || permission.module,
          permissions: [permission]
        });
      }
      return acc;
    }, [] as PermissionGroup[]);

    return groups.sort((a, b) => a.moduleName.localeCompare(b.moduleName));
  };

  const getModuleStats = (modulePermissions: Permission[]) => {
    const total = modulePermissions.length;
    const selected = modulePermissions.filter(p => selectedPermissions.includes(p.id)).length;
    return { total, selected };
  };

  const isModuleFullySelected = (modulePermissions: Permission[]) => {
    return modulePermissions.every(p => selectedPermissions.includes(p.id));
  };

  const isModulePartiallySelected = (modulePermissions: Permission[]) => {
    const selectedCount = modulePermissions.filter(p => selectedPermissions.includes(p.id)).length;
    return selectedCount > 0 && selectedCount < modulePermissions.length;
  };

  const permissionGroups = getPermissionGroups();
  const hasChanges = JSON.stringify(selectedPermissions.sort()) !== JSON.stringify(rolePermissions.sort());

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-4xl max-h-[80vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Shield className="w-5 h-5" />
            <span>配置角色权限 - {role.name}</span>
          </DialogTitle>
        </DialogHeader>

        <div className="flex flex-col space-y-4 overflow-hidden">
          {/* 搜索栏 */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4 dark:text-gray-500" />
            <Input
              placeholder="搜索权限..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* 统计信息 */}
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg dark:bg-gray-800/50">
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                已选择: <span className="font-medium text-blue-600 dark:text-blue-400">{selectedPermissions.length}</span>
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                总计: <span className="font-medium">{allPermissions.length}</span>
              </div>
            </div>
            {hasChanges && (
              <Badge variant="outline" className="text-orange-600 border-orange-200 dark:text-orange-400">
                有未保存的更改
              </Badge>
            )}
          </div>

          {/* 权限列表 */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex justify-center py-8">
                <div className="text-gray-500 dark:text-gray-400">加载中...</div>
              </div>
            ) : (
              <div className="space-y-4">
                {permissionGroups.map((group) => {
                  const stats = getModuleStats(group.permissions);
                  const isFullySelected = isModuleFullySelected(group.permissions);
                  const isPartiallySelected = isModulePartiallySelected(group.permissions);

                  return (
                    <div key={group.module} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <Checkbox
                            checked={isFullySelected}
                            indeterminate={isPartiallySelected}
                            onCheckedChange={(checked) => 
                              handleModuleToggle(group.permissions, checked as boolean)
                            }
                          />
                          <h3 className="font-medium text-gray-900 dark:text-gray-100">{group.moduleName}</h3>
                          <Badge variant="outline">
                            {stats.selected}/{stats.total}
                          </Badge>
                        </div>
                        <div className="flex items-center space-x-2">
                          {isFullySelected && <Check className="w-4 h-4 text-green-500 dark:text-green-400" />}
                          {isPartiallySelected && <div className="w-2 h-2 bg-orange-400 rounded-full" />}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                        {group.permissions.map((permission) => (
                          <div
                            key={permission.id}
                            className="flex items-center space-x-2 p-2 rounded border hover:bg-gray-50 dark:bg-gray-800/50 dark:hover:bg-gray-800"
                          >
                            <Checkbox
                              checked={selectedPermissions.includes(permission.id)}
                              onCheckedChange={(checked) => 
                                handlePermissionToggle(permission.id, checked as boolean)
                              }
                            />
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium text-gray-900 truncate dark:text-gray-100">
                                {permission.name}
                              </div>
                              <div className="text-xs text-gray-500 font-mono dark:text-gray-400">
                                {permission.code}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 操作按钮 */}
          <div className="flex justify-end space-x-2 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSaving}
            >
              取消
            </Button>
            <Button
              onClick={handleSave}
              disabled={isSaving || !hasChanges}
            >
              {isSaving ? '保存中...' : '保存'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};