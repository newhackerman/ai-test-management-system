import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { AlertCircle, CheckCircle, Clock, Loader2, Play, RotateCcw, Zap } from 'lucide-react';

import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/Dialog';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';
import { Switch } from '../ui/Switch';
import { Textarea } from '../ui/Textarea';
import { aiModelConfigService } from '../../services/aiModelConfigService';
import { AIModelConfig, AIModelTestRequest, AIModelTestResponse } from '../../types/aiModelConfig';

interface AIModelTestDialogProps {
  config: AIModelConfig;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const AIModelTestDialog: React.FC<AIModelTestDialogProps> = ({
  config,
  open,
  onOpenChange,
}) => {
  const [testMessage, setTestMessage] = useState('你好，请用一句话确认当前模型可以正常响应。');
  const [useCustomParams, setUseCustomParams] = useState(false);
  const [customTemperature, setCustomTemperature] = useState('0.7');
  const [customMaxTokens, setCustomMaxTokens] = useState('100');
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<AIModelTestResponse | null>(null);

  const reset = () => {
    setTestMessage('你好，请用一句话确认当前模型可以正常响应。');
    setUseCustomParams(false);
    setCustomTemperature('0.7');
    setCustomMaxTokens('100');
    setResult(null);
  };

  const runTest = async () => {
    if (!testMessage.trim()) {
      toast.error('请输入测试消息');
      return;
    }

    const payload: AIModelTestRequest = {
      test_message: testMessage.trim(),
      use_custom_params: useCustomParams,
      custom_temperature: useCustomParams ? Number(customTemperature) : undefined,
      custom_max_tokens: useCustomParams ? Number(customMaxTokens) : undefined,
    };

    try {
      setTesting(true);
      setResult(null);
      const response = await aiModelConfigService.testModel(config.id, payload);
      setResult(response);
      if (response.success) {
        toast.success('模型测试成功');
      } else {
        toast.error(response.error || '模型测试失败');
      }
    } catch (error) {
      console.error('Failed to test AI model:', error);
      toast.error('执行模型测试失败');
    } finally {
      setTesting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>测试 AI 模型</DialogTitle>
          <DialogDescription>向“{config.display_name}”发送一条测试消息并查看响应结果。</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">模型信息</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <InfoItem label="显示名称" value={config.display_name} />
              <InfoItem label="模型名称" value={config.model_name} />
              <InfoItem label="供应商" value={config.provider} />
              <div className="space-y-1">
                <Label>状态</Label>
                <div className="flex gap-2">
                  <Badge variant={config.is_enabled ? 'default' : 'secondary'}>
                    {config.is_enabled ? '启用' : '禁用'}
                  </Badge>
                  {config.is_default && <Badge variant="outline">默认</Badge>}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">测试参数</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>测试消息</Label>
                <Textarea
                  rows={4}
                  value={testMessage}
                  onChange={(event) => setTestMessage(event.target.value)}
                  placeholder="输入要发送给模型的测试内容"
                />
              </div>

              <Switch
                checked={useCustomParams}
                onChange={(event) => setUseCustomParams(event.target.checked)}
                label="使用自定义参数"
              />

              {useCustomParams && (
                <div className="grid gap-4 rounded-md border p-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>温度</Label>
                    <Input
                      type="number"
                      min="0"
                      max="2"
                      step="0.1"
                      value={customTemperature}
                      onChange={(event) => setCustomTemperature(event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>最大 Token</Label>
                    <Input
                      type="number"
                      min="1"
                      step="1"
                      value={customMaxTokens}
                      onChange={(event) => setCustomMaxTokens(event.target.value)}
                    />
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={reset} disabled={testing}>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  重置
                </Button>
                <Button type="button" onClick={runTest} disabled={testing}>
                  {testing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                  开始测试
                </Button>
              </div>
            </CardContent>
          </Card>

          {result && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  {result.success ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                  )}
                  测试结果
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-3">
                  <Metric icon={<Clock className="h-4 w-4" />} label="响应时间" value={`${result.response_time?.toFixed(2) ?? '-'}s`} />
                  <Metric icon={<Zap className="h-4 w-4" />} label="Token" value={result.tokens_used?.toString() ?? '-'} />
                  <Metric label="成本" value={result.cost == null ? '-' : `¥${result.cost.toFixed(6)}`} />
                </div>

                {result.response_text && (
                  <div className="space-y-2">
                    <Label>模型响应</Label>
                    <div className="whitespace-pre-wrap rounded-md border bg-muted/40 p-3 text-sm">
                      {result.response_text}
                    </div>
                  </div>
                )}

                {result.error && (
                  <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:text-red-400 dark:bg-red-900/20 dark:border-red-800">
                    {result.error}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

const InfoItem: React.FC<{ label: string; value?: React.ReactNode }> = ({ label, value }) => (
  <div className="space-y-1">
    <Label>{label}</Label>
    <div className="text-sm text-muted-foreground">{value || '-'}</div>
  </div>
);

const Metric: React.FC<{ icon?: React.ReactNode; label: string; value: string }> = ({ icon, label, value }) => (
  <div className="rounded-md border p-3">
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      {icon}
      {label}
    </div>
    <div className="mt-1 text-lg font-semibold">{value}</div>
  </div>
);
