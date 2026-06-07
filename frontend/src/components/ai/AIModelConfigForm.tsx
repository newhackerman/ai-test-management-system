import React, { useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { Eye, EyeOff, Loader2, Plus, X } from 'lucide-react';

import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/Select';
import { Switch } from '../ui/Switch';
import { Textarea } from '../ui/Textarea';
import { aiModelConfigService } from '../../services/aiModelConfigService';
import {
  AIModelConfig,
  AIModelConfigCreate,
  AIModelConfigUpdate,
  AIProvider,
} from '../../types/aiModelConfig';

interface AIModelConfigFormProps {
  initialData?: AIModelConfig;
  onSuccess: (config: AIModelConfig) => void;
  onCancel: () => void;
}

type FormState = {
  provider: AIProvider;
  model_name: string;
  display_name: string;
  description: string;
  version: string;
  api_endpoint: string;
  api_key: string;
  api_version: string;
  max_tokens: number;
  temperature: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  is_enabled: boolean;
  is_default: boolean;
  is_public: boolean;
  priority: number;
  daily_quota: string;
  monthly_quota: string;
  user_daily_quota: string;
  concurrent_limit: number;
  cost_per_input_token: string;
  cost_per_output_token: string;
  cost_per_request: string;
  capabilities: string;
  supported_languages: string;
  use_cases: string;
};

const providerLabels: Record<AIProvider, string> = {
  [AIProvider.OPENAI]: 'OpenAI',
  [AIProvider.ANTHROPIC]: 'Anthropic',
  [AIProvider.BAIDU_WENXIN]: '百度文心',
  [AIProvider.ALIYUN_TONGYI]: '阿里通义',
  [AIProvider.GOOGLE_GEMINI]: 'Google Gemini',
  [AIProvider.ZHIPU_CHATGLM]: '智谱 ChatGLM',
  [AIProvider.XUNFEI_XINGHUO]: '讯飞星火',
  [AIProvider.CUSTOM]: '自定义',
};

const defaultForm: FormState = {
  provider: AIProvider.OPENAI,
  model_name: '',
  display_name: '',
  description: '',
  version: '',
  api_endpoint: '',
  api_key: '',
  api_version: '',
  max_tokens: 4000,
  temperature: 0.7,
  top_p: 1,
  frequency_penalty: 0,
  presence_penalty: 0,
  is_enabled: true,
  is_default: false,
  is_public: true,
  priority: 0,
  daily_quota: '',
  monthly_quota: '',
  user_daily_quota: '',
  concurrent_limit: 10,
  cost_per_input_token: '',
  cost_per_output_token: '',
  cost_per_request: '',
  capabilities: '',
  supported_languages: '',
  use_cases: '',
};

const toTextList = (value?: string[]) => value?.join(', ') ?? '';
const parseList = (value: string) =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

const optionalNumber = (value: string) => {
  if (value.trim() === '') return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
};

const buildInitialState = (config?: AIModelConfig): FormState => {
  if (!config) return defaultForm;

  return {
    provider: config.provider,
    model_name: config.model_name,
    display_name: config.display_name,
    description: config.description ?? '',
    version: config.version ?? '',
    api_endpoint: config.api_endpoint ?? '',
    api_key: config.api_key ?? '',
    api_version: config.api_version ?? '',
    max_tokens: config.max_tokens ?? 4000,
    temperature: config.temperature ?? 0.7,
    top_p: config.top_p ?? 1,
    frequency_penalty: config.frequency_penalty ?? 0,
    presence_penalty: config.presence_penalty ?? 0,
    is_enabled: config.is_enabled,
    is_default: config.is_default,
    is_public: config.is_public,
    priority: config.priority ?? 0,
    daily_quota: config.daily_quota?.toString() ?? '',
    monthly_quota: config.monthly_quota?.toString() ?? '',
    user_daily_quota: config.user_daily_quota?.toString() ?? '',
    concurrent_limit: config.concurrent_limit ?? 10,
    cost_per_input_token: config.cost_per_input_token?.toString() ?? '',
    cost_per_output_token: config.cost_per_output_token?.toString() ?? '',
    cost_per_request: config.cost_per_request?.toString() ?? '',
    capabilities: toTextList(config.capabilities),
    supported_languages: toTextList(config.supported_languages),
    use_cases: toTextList(config.use_cases),
  };
};

export const AIModelConfigForm: React.FC<AIModelConfigFormProps> = ({
  initialData,
  onSuccess,
  onCancel,
}) => {
  const [form, setForm] = useState<FormState>(() => buildInitialState(initialData));
  const [showApiKey, setShowApiKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [headers, setHeaders] = useState<Array<{ key: string; value: string }>>(() =>
    Object.entries(initialData?.headers ?? {}).map(([key, value]) => ({ key, value: String(value) })),
  );
  const [stopSequences, setStopSequences] = useState<string[]>(initialData?.stop_sequences ?? []);

  const isEditing = Boolean(initialData);

  const payload = useMemo(() => {
    const base = {
      display_name: form.display_name.trim(),
      description: form.description.trim() || undefined,
      version: form.version.trim() || undefined,
      api_endpoint: form.api_endpoint.trim() || undefined,
      api_key: form.api_key.trim() || undefined,
      api_version: form.api_version.trim() || undefined,
      max_tokens: Number(form.max_tokens),
      temperature: Number(form.temperature),
      top_p: Number(form.top_p),
      frequency_penalty: Number(form.frequency_penalty),
      presence_penalty: Number(form.presence_penalty),
      is_enabled: form.is_enabled,
      is_default: form.is_default,
      is_public: form.is_public,
      priority: Number(form.priority),
      daily_quota: optionalNumber(form.daily_quota),
      monthly_quota: optionalNumber(form.monthly_quota),
      user_daily_quota: optionalNumber(form.user_daily_quota),
      concurrent_limit: Number(form.concurrent_limit),
      cost_per_input_token: optionalNumber(form.cost_per_input_token),
      cost_per_output_token: optionalNumber(form.cost_per_output_token),
      cost_per_request: optionalNumber(form.cost_per_request),
      capabilities: parseList(form.capabilities),
      supported_languages: parseList(form.supported_languages),
      use_cases: parseList(form.use_cases),
      stop_sequences: stopSequences.filter(Boolean),
      headers: Object.fromEntries(headers.filter((item) => item.key.trim()).map((item) => [item.key.trim(), item.value])),
    };

    return {
      ...base,
      provider: form.provider,
      model_name: form.model_name.trim(),
    };
  }, [form, headers, stopSequences]);

  const setField = <K extends keyof FormState>(field: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const validate = () => {
    if (!form.model_name.trim()) return '请填写模型名称';
    if (!form.display_name.trim()) return '请填写显示名称';
    if (form.max_tokens < 1) return '最大 Token 数必须大于 0';
    if (form.temperature < 0 || form.temperature > 2) return '温度参数必须在 0 到 2 之间';
    if (form.top_p < 0 || form.top_p > 1) return 'Top P 必须在 0 到 1 之间';
    if (form.concurrent_limit < 1) return '并发限制必须大于 0';
    return null;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const error = validate();
    if (error) {
      toast.error(error);
      return;
    }

    try {
      setLoading(true);
      const saved = isEditing && initialData
        ? await aiModelConfigService.updateModelConfig(initialData.id, payload as AIModelConfigUpdate)
        : await aiModelConfigService.createModelConfig(payload as AIModelConfigCreate);
      toast.success(isEditing ? '模型配置已更新' : '模型配置已创建');
      onSuccess(saved);
    } catch (err) {
      console.error('Failed to save AI model config:', err);
      toast.error('保存模型配置失败，请检查接口和必填字段');
    } finally {
      setLoading(false);
    }
  };

  const addHeader = () => setHeaders((prev) => [...prev, { key: '', value: '' }]);
  const updateHeader = (index: number, field: 'key' | 'value', value: string) => {
    setHeaders((prev) => prev.map((item, i) => (i === index ? { ...item, [field]: value } : item)));
  };
  const removeHeader = (index: number) => setHeaders((prev) => prev.filter((_, i) => i !== index));
  const addStopSequence = () => setStopSequences((prev) => [...prev, '']);
  const updateStopSequence = (index: number, value: string) => {
    setStopSequences((prev) => prev.map((item, i) => (i === index ? value : item)));
  };
  const removeStopSequence = (index: number) => setStopSequences((prev) => prev.filter((_, i) => i !== index));

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">基础信息</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>供应商</Label>
            <Select
              value={form.provider}
              onValueChange={(value) => setField('provider', value as AIProvider)}
              disabled={isEditing}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择供应商" />
              </SelectTrigger>
              <SelectContent>
                {Object.values(AIProvider).map((provider) => (
                  <SelectItem key={provider} value={provider}>
                    {providerLabels[provider]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>模型名称</Label>
            <Input
              value={form.model_name}
              onChange={(event) => setField('model_name', event.target.value)}
              placeholder="例如 gpt-4o-mini"
              disabled={isEditing}
            />
          </div>

          <div className="space-y-2">
            <Label>显示名称</Label>
            <Input
              value={form.display_name}
              onChange={(event) => setField('display_name', event.target.value)}
              placeholder="用于页面展示的名称"
            />
          </div>

          <div className="space-y-2">
            <Label>版本</Label>
            <Input value={form.version} onChange={(event) => setField('version', event.target.value)} />
          </div>

          <div className="space-y-2 md:col-span-2">
            <Label>描述</Label>
            <Textarea
              value={form.description}
              onChange={(event) => setField('description', event.target.value)}
              placeholder="填写模型用途、适用场景或注意事项"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">接口配置</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2 md:col-span-2">
            <Label>API Endpoint</Label>
            <Input
              value={form.api_endpoint}
              onChange={(event) => setField('api_endpoint', event.target.value)}
              placeholder="https://api.example.com/v1"
            />
          </div>

          <div className="space-y-2">
            <Label>API Key</Label>
            <div className="flex gap-2">
              <Input
                type={showApiKey ? 'text' : 'password'}
                value={form.api_key}
                onChange={(event) => setField('api_key', event.target.value)}
                autoComplete="new-password"
              />
              <Button type="button" variant="outline" size="icon" onClick={() => setShowApiKey((prev) => !prev)}>
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label>API 版本</Label>
            <Input value={form.api_version} onChange={(event) => setField('api_version', event.target.value)} />
          </div>

          <div className="space-y-3 md:col-span-2">
            <div className="flex items-center justify-between">
              <Label>自定义请求头</Label>
              <Button type="button" variant="outline" size="sm" onClick={addHeader}>
                <Plus className="mr-2 h-4 w-4" />
                添加
              </Button>
            </div>
            {headers.map((header, index) => (
              <div key={index} className="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
                <Input placeholder="Header 名称" value={header.key} onChange={(event) => updateHeader(index, 'key', event.target.value)} />
                <Input placeholder="Header 值" value={header.value} onChange={(event) => updateHeader(index, 'value', event.target.value)} />
                <Button type="button" variant="ghost" size="icon" onClick={() => removeHeader(index)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">参数与限制</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <NumberField label="最大 Token" value={form.max_tokens} onChange={(value) => setField('max_tokens', value)} min={1} />
          <NumberField label="温度" value={form.temperature} onChange={(value) => setField('temperature', value)} min={0} max={2} step={0.1} />
          <NumberField label="Top P" value={form.top_p} onChange={(value) => setField('top_p', value)} min={0} max={1} step={0.1} />
          <NumberField label="频率惩罚" value={form.frequency_penalty} onChange={(value) => setField('frequency_penalty', value)} min={-2} max={2} step={0.1} />
          <NumberField label="存在惩罚" value={form.presence_penalty} onChange={(value) => setField('presence_penalty', value)} min={-2} max={2} step={0.1} />
          <NumberField label="并发限制" value={form.concurrent_limit} onChange={(value) => setField('concurrent_limit', value)} min={1} />
          <NumberField label="优先级" value={form.priority} onChange={(value) => setField('priority', value)} min={0} />

          <TextNumberField label="每日总配额" value={form.daily_quota} onChange={(value) => setField('daily_quota', value)} />
          <TextNumberField label="每月总配额" value={form.monthly_quota} onChange={(value) => setField('monthly_quota', value)} />
          <TextNumberField label="用户每日配额" value={form.user_daily_quota} onChange={(value) => setField('user_daily_quota', value)} />
          <TextNumberField label="输入 Token 成本" value={form.cost_per_input_token} onChange={(value) => setField('cost_per_input_token', value)} step="0.000001" />
          <TextNumberField label="输出 Token 成本" value={form.cost_per_output_token} onChange={(value) => setField('cost_per_output_token', value)} step="0.000001" />
          <TextNumberField label="单次请求成本" value={form.cost_per_request} onChange={(value) => setField('cost_per_request', value)} step="0.000001" />

          <div className="space-y-3 md:col-span-3">
            <div className="flex items-center justify-between">
              <Label>停止序列</Label>
              <Button type="button" variant="outline" size="sm" onClick={addStopSequence}>
                <Plus className="mr-2 h-4 w-4" />
                添加
              </Button>
            </div>
            {stopSequences.map((item, index) => (
              <div key={index} className="grid gap-2 md:grid-cols-[1fr_auto]">
                <Input value={item} onChange={(event) => updateStopSequence(index, event.target.value)} />
                <Button type="button" variant="ghost" size="icon" onClick={() => removeStopSequence(index)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">标签与状态</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>能力标签</Label>
            <Input value={form.capabilities} onChange={(event) => setField('capabilities', event.target.value)} placeholder="对话, 代码, 总结" />
          </div>
          <div className="space-y-2">
            <Label>支持语言</Label>
            <Input value={form.supported_languages} onChange={(event) => setField('supported_languages', event.target.value)} placeholder="中文, 英文" />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label>使用场景</Label>
            <Input value={form.use_cases} onChange={(event) => setField('use_cases', event.target.value)} placeholder="测试用例生成, 缺陷分析" />
          </div>
          <Switch checked={form.is_enabled} onChange={(event) => setField('is_enabled', event.target.checked)} label="启用模型" />
          <Switch checked={form.is_default} onChange={(event) => setField('is_default', event.target.checked)} label="设为默认模型" />
          <Switch checked={form.is_public} onChange={(event) => setField('is_public', event.target.checked)} label="公开给用户使用" />
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
          取消
        </Button>
        <Button type="submit" disabled={loading}>
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEditing ? '保存修改' : '创建模型'}
        </Button>
      </div>
    </form>
  );
};

interface NumberFieldProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
}

const NumberField: React.FC<NumberFieldProps> = ({ label, value, onChange, min, max, step = 1 }) => (
  <div className="space-y-2">
    <Label>{label}</Label>
    <Input
      type="number"
      value={value}
      min={min}
      max={max}
      step={step}
      onChange={(event) => onChange(Number(event.target.value))}
    />
  </div>
);

interface TextNumberFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  step?: string;
}

const TextNumberField: React.FC<TextNumberFieldProps> = ({ label, value, onChange, step = '1' }) => (
  <div className="space-y-2">
    <Label>{label}</Label>
    <Input type="number" value={value} min="0" step={step} onChange={(event) => onChange(event.target.value)} />
  </div>
);
