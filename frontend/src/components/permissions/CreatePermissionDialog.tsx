import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { createPermission } from '@/api/permission';
import { toast } from 'react-hot-toast';

interface CreatePermissionDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const PERMISSION_MODULES = [
  { value: 'user_management', label: '用户管理' },
  { value: 'role_management', label: '角色管理' },
  { value: 'permission_management', label: '权限管理' },
  { value: 'project_management', label: '项目管理' },
  { value: 'requirement_management', label: '需求管理' },
  { value: 'test_management', label: '测试管理' },
  { value: 'system_config', label: '系统配置' },
  { value: 'audit', label: '审计日志' },
  { value: 'monitoring', label: '系统监控' },
  { value: 'data_management', label: '数据管理' }
];

const PERMISSION_ACTIONS = [
  { value: 'create', label: '创建' },
  { value: 'read', label: '查看' },
  { value: 'update', label: '更新' },
  { value: 'delete', label: '删除' },
  { value: 'list', label: '列表' },
  { value: 'export', label: '导出' },
  { value: 'import', label: '导入' },
  { value: 'assign', label: '分配' },
  { value: 'approve', label: '审批' },
  { value: 'execute', label: '执行' }
];

export const CreatePermissionDialog: React.FC<CreatePermissionDialogProps> = ({
  open,
  onClose,
  onSuccess
}) => {
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    module: '',
    action: '',
    resource: '',
    description: ''
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim() || !formData.code.trim() || !formData.module || !formData.action) {
      toast.error('请填写必填字段');
      return;
    }

    setIsLoading(true);
    try {
      await createPermission(formData);
      toast.success('权限创建成功');
      onSuccess();
      handleClose();
    } catch (error: any) {
      toast.error(error.message || '创建权限失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({
      name: '',
      code: '',
      module: '',
      action: '',
      resource: '',
      description: ''
    });
    onClose();
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // 自动生成权限代码
    if (field === 'module' || field === 'action') {
      const newFormData = { ...formData, [field]: value };
      if (newFormData.module && newFormData.action) {
        const code = `${newFormData.module}:${newFormData.action}`;
        setFormData(prev => ({ ...prev, [field]: value, code }));
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>创建权限</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">权限名称 *</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              placeholder="请输入权限名称"
              disabled={isLoading}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="module">所属模块 *</Label>
              <Select
                value={formData.module}
                onValueChange={(value) => handleInputChange('module', value)}
                disabled={isLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择模块" />
                </SelectTrigger>
                <SelectContent>
                  {PERMISSION_MODULES.map((module) => (
                    <SelectItem key={module.value} value={module.value}>
                      {module.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="action">操作类型 *</Label>
              <Select
                value={formData.action}
                onValueChange={(value) => handleInputChange('action', value)}
                disabled={isLoading}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择操作" />
                </SelectTrigger>
                <SelectContent>
                  {PERMISSION_ACTIONS.map((action) => (
                    <SelectItem key={action.value} value={action.value}>
                      {action.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="code">权限代码 *</Label>
            <Input
              id="code"
              value={formData.code}
              onChange={(e) => handleInputChange('code', e.target.value)}
              placeholder="权限代码（自动生成）"
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="resource">资源标识</Label>
            <Input
              id="resource"
              value={formData.resource}
              onChange={(e) => handleInputChange('resource', e.target.value)}
              placeholder="请输入资源标识（可选）"
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">权限描述</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="请输入权限描述"
              disabled={isLoading}
              rows={3}
            />
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isLoading}
            >
              取消
            </Button>
            <Button
              type="submit"
              disabled={isLoading}
            >
              {isLoading ? '创建中...' : '创建'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};