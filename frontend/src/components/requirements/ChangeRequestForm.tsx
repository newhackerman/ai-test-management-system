import React, { useEffect, useState } from 'react';
import { AlertTriangle, Calculator, FileText } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Textarea } from '@/components/ui/Textarea';
import type { ChangePriority, ChangeType, Requirement } from '@/types/requirement';

interface ChangeRequestFormData {
  requirement_id: number;
  title: string;
  description: string;
  reason: string;
  change_type: ChangeType;
  priority: ChangePriority;
  target_date?: string;
  effort_estimate?: number;
  cost_estimate?: number;
  risk_assessment?: string;
  impact_analysis?: string;
}

interface ChangeRequestFormProps {
  initialData?: Partial<ChangeRequestFormData>;
  requirementId?: number;
  onSubmit: (data: ChangeRequestFormData) => void | Promise<void>;
  onCancel: () => void;
}

const mockRequirements: Requirement[] = [
  {
    id: 101,
    requirement_code: 'REQ-2024-001',
    project_id: 1,
    title: '用户登录功能',
    description: '实现用户登录认证能力',
    requirement_type: 'FUNCTIONAL',
    priority: 'HIGH',
    business_value: 'CORE',
    status: 'IN_DEVELOPMENT',
    creator_id: 1,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    version: 1
  },
  {
    id: 102,
    requirement_code: 'REQ-2024-002',
    project_id: 1,
    title: '报表管理功能',
    description: '实现报表生成和管理功能',
    requirement_type: 'FUNCTIONAL',
    priority: 'MEDIUM',
    business_value: 'IMPORTANT',
    status: 'APPROVED',
    creator_id: 1,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    version: 1
  }
];

const changeTypeOptions: Array<{ value: ChangeType; label: string }> = [
  { value: 'ADDITION', label: '新增功能' },
  { value: 'MODIFICATION', label: '修改功能' },
  { value: 'DELETION', label: '删除功能' },
  { value: 'CLARIFICATION', label: '澄清说明' }
];

const priorityOptions: Array<{ value: ChangePriority; label: string }> = [
  { value: 'EMERGENCY', label: '紧急' },
  { value: 'HIGH', label: '高' },
  { value: 'MEDIUM', label: '中' },
  { value: 'LOW', label: '低' }
];

export function ChangeRequestForm({ initialData, requirementId, onSubmit, onCancel }: ChangeRequestFormProps) {
  const [formData, setFormData] = useState<ChangeRequestFormData>({
    requirement_id: requirementId || 0,
    title: '',
    description: '',
    reason: '',
    change_type: 'MODIFICATION',
    priority: 'MEDIUM',
    target_date: '',
    effort_estimate: undefined,
    cost_estimate: undefined,
    risk_assessment: '',
    impact_analysis: '',
    ...initialData
  });
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [selectedRequirement, setSelectedRequirement] = useState<Requirement | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setRequirements(mockRequirements);
  }, []);

  useEffect(() => {
    setSelectedRequirement(requirements.find((requirement) => requirement.id === formData.requirement_id) || null);
  }, [formData.requirement_id, requirements]);

  const handleInputChange = (field: keyof ChangeRequestFormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const validateForm = () => {
    const nextErrors: Record<string, string> = {};
    if (!formData.requirement_id) nextErrors.requirement_id = '请选择需求';
    if (!formData.title.trim()) nextErrors.title = '请输入变更标题';
    if (!formData.description.trim()) nextErrors.description = '请输入变更描述';
    if (!formData.reason.trim()) nextErrors.reason = '请输入变更原因';
    if (formData.effort_estimate != null && formData.effort_estimate <= 0) nextErrors.effort_estimate = '工作量估算必须大于 0';
    if (formData.cost_estimate != null && formData.cost_estimate <= 0) nextErrors.cost_estimate = '成本估算必须大于 0';
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    try {
      await onSubmit(formData);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <FileText className="mr-2 h-5 w-5" />
            基本信息
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field label="关联需求 *" error={errors.requirement_id}>
            <select
              className="h-10 w-full rounded-md border px-3 text-sm"
              value={formData.requirement_id}
              onChange={(event) => handleInputChange('requirement_id', Number(event.target.value))}
              disabled={Boolean(requirementId)}
            >
              <option value={0}>请选择需求</option>
              {requirements.map((requirement) => (
                <option key={requirement.id} value={requirement.id}>
                  {requirement.requirement_code} - {requirement.title}
                </option>
              ))}
            </select>
          </Field>

          {selectedRequirement && (
            <Alert>
              <AlertDescription>
                <div className="grid gap-1 text-sm sm:grid-cols-2">
                  <div>需求编号：{selectedRequirement.requirement_code}</div>
                  <div>当前状态：{selectedRequirement.status}</div>
                  <div>需求标题：{selectedRequirement.title}</div>
                  <div>优先级：{selectedRequirement.priority}</div>
                </div>
              </AlertDescription>
            </Alert>
          )}

          <Field label="变更标题 *" error={errors.title}>
            <Input value={formData.title} onChange={(event) => handleInputChange('title', event.target.value)} placeholder="请输入变更标题" />
          </Field>

          <div className="grid gap-4 md:grid-cols-2">
            <Field label="变更类型 *">
              <select
                className="h-10 w-full rounded-md border px-3 text-sm"
                value={formData.change_type}
                onChange={(event) => handleInputChange('change_type', event.target.value as ChangeType)}
              >
                {changeTypeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="优先级 *">
              <select
                className="h-10 w-full rounded-md border px-3 text-sm"
                value={formData.priority}
                onChange={(event) => handleInputChange('priority', event.target.value as ChangePriority)}
              >
                {priorityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field label="目标完成日期">
            <Input type="date" value={formData.target_date || ''} onChange={(event) => handleInputChange('target_date', event.target.value)} />
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <AlertTriangle className="mr-2 h-5 w-5" />
            变更详情
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field label="变更描述 *" error={errors.description}>
            <Textarea
              value={formData.description}
              onChange={(event) => handleInputChange('description', event.target.value)}
              placeholder="详细描述需要变更的内容..."
              rows={4}
            />
          </Field>

          <Field label="变更原因 *" error={errors.reason}>
            <Textarea
              value={formData.reason}
              onChange={(event) => handleInputChange('reason', event.target.value)}
              placeholder="说明为什么需要进行此变更..."
              rows={3}
            />
          </Field>

          <Field label="影响分析">
            <Textarea
              value={formData.impact_analysis || ''}
              onChange={(event) => handleInputChange('impact_analysis', event.target.value)}
              placeholder="分析对系统、其他需求、项目进度和质量的影响..."
              rows={3}
            />
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Calculator className="mr-2 h-5 w-5" />
            估算信息
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="工作量估算（人天）" error={errors.effort_estimate}>
              <Input
                type="number"
                step="0.5"
                min="0"
                value={formData.effort_estimate ?? ''}
                onChange={(event) => handleInputChange('effort_estimate', event.target.value ? Number(event.target.value) : undefined)}
                placeholder="0.0"
              />
            </Field>
            <Field label="成本估算（元）" error={errors.cost_estimate}>
              <Input
                type="number"
                min="0"
                value={formData.cost_estimate ?? ''}
                onChange={(event) => handleInputChange('cost_estimate', event.target.value ? Number(event.target.value) : undefined)}
                placeholder="0"
              />
            </Field>
          </div>

          <Field label="风险评估">
            <Textarea
              value={formData.risk_assessment || ''}
              onChange={(event) => handleInputChange('risk_assessment', event.target.value)}
              placeholder="评估实施该变更可能面临的风险和应对措施..."
              rows={3}
            />
          </Field>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
          取消
        </Button>
        <Button type="submit" disabled={loading}>
          {loading ? '提交中...' : '提交变更请求'}
        </Button>
      </div>
    </form>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}

export default ChangeRequestForm;
