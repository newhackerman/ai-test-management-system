import React, { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Search, Filter, Download, Check, X, Minus } from 'lucide-react';
import type { PermissionMatrix } from '@/types';

interface PermissionMatrixViewProps {
  matrix: PermissionMatrix;
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

export const PermissionMatrixView: React.FC<PermissionMatrixViewProps> = ({ matrix }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedModule, setSelectedModule] = useState('');
  const [selectedRoleType, setSelectedRoleType] = useState('');

  // 获取所有模块
  const modules = Array.from(new Set(matrix.permissions.map(p => p.module)));
  
  // 筛选权限
  const filteredPermissions = matrix.permissions.filter(permission => {
    const matchesSearch = permission.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         permission.code.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesModule = !selectedModule || permission.module === selectedModule;
    return matchesSearch && matchesModule;
  });

  // 筛选角色
  const filteredRoles = matrix.roles.filter(role => {
    if (!selectedRoleType) return true;
    // 这里需要根据实际的角色类型字段来判断
    // 假设系统角色的code包含'admin'或'system'
    const isSystemRole = role.code.includes('admin') || role.code.includes('system');
    return selectedRoleType === 'system' ? isSystemRole : !isSystemRole;
  });

  // 获取权限状态图标
  const getPermissionIcon = (roleCode: string, permissionCode: string) => {
    const hasPermission = matrix.matrix[roleCode]?.[permissionCode];
    
    if (hasPermission === true) {
      return <Check className="w-4 h-4 text-green-500" />;
    } else if (hasPermission === false) {
      return <X className="w-4 h-4 text-red-500" />;
    } else {
      return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  // 获取权限状态文本
  const getPermissionText = (roleCode: string, permissionCode: string) => {
    const hasPermission = matrix.matrix[roleCode]?.[permissionCode];
    
    if (hasPermission === true) {
      return '有权限';
    } else if (hasPermission === false) {
      return '无权限';
    } else {
      return '未设置';
    }
  };

  // 获取权限状态样式
  const getPermissionCellClass = (roleCode: string, permissionCode: string) => {
    const hasPermission = matrix.matrix[roleCode]?.[permissionCode];
    
    if (hasPermission === true) {
      return 'bg-green-50 border-green-200';
    } else if (hasPermission === false) {
      return 'bg-red-50 border-red-200';
    } else {
      return 'bg-gray-50 border-gray-200';
    }
  };

  // 导出矩阵数据
  const handleExport = () => {
    const csvContent = [
      // 表头
      ['权限/角色', ...filteredRoles.map(role => role.name)].join(','),
      // 数据行
      ...filteredPermissions.map(permission => [
        permission.name,
        ...filteredRoles.map(role => 
          getPermissionText(role.code, permission.code)
        )
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', '权限矩阵.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 按模块分组权限
  const permissionsByModule = filteredPermissions.reduce((acc, permission) => {
    const module = permission.module;
    if (!acc[module]) {
      acc[module] = [];
    }
    acc[module].push(permission);
    return acc;
  }, {} as Record<string, typeof filteredPermissions>);

  return (
    <div className="space-y-4">
      {/* 筛选控件 */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-64">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            placeholder="搜索权限..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select value={selectedModule} onValueChange={setSelectedModule}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="选择模块" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部模块</SelectItem>
            {modules.map(module => (
              <SelectItem key={module} value={module}>
                {MODULE_NAMES[module] || module}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={selectedRoleType} onValueChange={setSelectedRoleType}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="角色类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部角色</SelectItem>
            <SelectItem value="system">系统角色</SelectItem>
            <SelectItem value="custom">自定义角色</SelectItem>
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          onClick={() => {
            setSearchTerm('');
            setSelectedModule('');
            setSelectedRoleType('');
          }}
          className="flex items-center space-x-2"
        >
          <Filter className="w-4 h-4" />
          <span>重置</span>
        </Button>

        <Button
          variant="outline"
          onClick={handleExport}
          className="flex items-center space-x-2"
        >
          <Download className="w-4 h-4" />
          <span>导出</span>
        </Button>
      </div>

      {/* 统计信息 */}
      <div className="flex items-center space-x-6 p-3 bg-gray-50 rounded-lg">
        <div className="text-sm text-gray-600">
          角色数量: <span className="font-medium">{filteredRoles.length}</span>
        </div>
        <div className="text-sm text-gray-600">
          权限数量: <span className="font-medium">{filteredPermissions.length}</span>
        </div>
        <div className="text-sm text-gray-600">
          模块数量: <span className="font-medium">{Object.keys(permissionsByModule).length}</span>
        </div>
      </div>

      {/* 权限矩阵表格 */}
      <div className="border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="sticky left-0 bg-gray-50 px-4 py-3 text-left font-medium text-gray-900 border-r min-w-64">
                  权限名称
                </th>
                {filteredRoles.map(role => (
                  <th
                    key={role.id}
                    className="px-3 py-3 text-center font-medium text-gray-900 min-w-24 border-r last:border-r-0"
                  >
                    <div className="space-y-1">
                      <div className="text-sm">{role.name}</div>
                      <Badge 
                        variant="outline" 
                        className="text-xs"
                      >
                        {role.code.includes('admin') || role.code.includes('system') ? '系统' : '自定义'}
                      </Badge>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(permissionsByModule).map(([module, permissions]) => (
                <React.Fragment key={module}>
                  {/* 模块分组标题 */}
                  <tr className="bg-blue-50">
                    <td
                      colSpan={filteredRoles.length + 1}
                      className="px-4 py-2 font-medium text-blue-900 border-b"
                    >
                      {MODULE_NAMES[module] || module} ({permissions.length} 个权限)
                    </td>
                  </tr>
                  
                  {/* 权限行 */}
                  {permissions.map(permission => (
                    <tr key={permission.id} className="hover:bg-gray-50">
                      <td className="sticky left-0 bg-white px-4 py-3 border-r border-b">
                        <div>
                          <div className="font-medium text-gray-900">{permission.name}</div>
                          <div className="text-sm text-gray-500 font-mono">{permission.code}</div>
                        </div>
                      </td>
                      {filteredRoles.map(role => (
                        <td
                          key={`${role.id}-${permission.id}`}
                          className={`px-3 py-3 text-center border-r border-b last:border-r-0 ${getPermissionCellClass(role.code, permission.code)}`}
                        >
                          <div className="flex items-center justify-center">
                            {getPermissionIcon(role.code, permission.code)}
                          </div>
                        </td>
                      ))}
                    </tr>
                  ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 图例 */}
      <div className="flex items-center justify-center space-x-6 p-3 bg-gray-50 rounded-lg">
        <div className="flex items-center space-x-2">
          <Check className="w-4 h-4 text-green-500" />
          <span className="text-sm text-gray-600">有权限</span>
        </div>
        <div className="flex items-center space-x-2">
          <X className="w-4 h-4 text-red-500" />
          <span className="text-sm text-gray-600">无权限</span>
        </div>
        <div className="flex items-center space-x-2">
          <Minus className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-600">未设置</span>
        </div>
      </div>
    </div>
  );
};