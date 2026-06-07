import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { Loader2, Plus, X } from 'lucide-react';

import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/Dialog';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/Select';
import { Textarea } from '../ui/Textarea';
import { useCreateConversation } from '../../hooks/useConversations';
import { ConversationGroup, ConversationResponse, CreateConversationRequest } from '../../services/conversation-service';

interface CreateConversationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (conversation: ConversationResponse) => void;
}

const templates = [
  { value: 'general', label: '通用对话', model: 'gpt-3.5-turbo', provider: 'OpenAI', prompt: '你是一个专业、友好的 AI 助手。' },
  { value: 'code_assistant', label: '代码助手', model: 'gpt-4', provider: 'OpenAI', prompt: '你是一个专业的编程助手，请提供准确、可执行的建议。' },
  { value: 'test_expert', label: '测试专家', model: 'gpt-4-turbo', provider: 'OpenAI', prompt: '你是测试专家，擅长测试用例设计、缺陷分析和质量改进。' },
  { value: 'document_writer', label: '文档写作', model: 'claude-3-sonnet', provider: 'Anthropic', prompt: '你擅长创建清晰、结构化的技术文档。' },
];

const groupLabels: Record<ConversationGroup, string> = {
  [ConversationGroup.WORK]: '工作',
  [ConversationGroup.STUDY]: '学习',
  [ConversationGroup.PROJECT]: '项目',
  [ConversationGroup.PERSONAL]: '个人',
  [ConversationGroup.RESEARCH]: '研究',
  [ConversationGroup.DEVELOPMENT]: '开发',
  [ConversationGroup.TESTING]: '测试',
  [ConversationGroup.OTHER]: '其他',
};

export function CreateConversationDialog({ open, onOpenChange, onSuccess }: CreateConversationDialogProps) {
  const [formData, setFormData] = useState<CreateConversationRequest>({
    title: '',
    template_type: 'general',
    ai_model: 'gpt-3.5-turbo',
    ai_provider: 'OpenAI',
    group: ConversationGroup.WORK,
    tags: [],
    goal: '',
    system_prompt: templates[0].prompt,
  });
  const [newTag, setNewTag] = useState('');
  const createMutation = useCreateConversation();

  const setField = <K extends keyof CreateConversationRequest>(field: K, value: CreateConversationRequest[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const applyTemplate = (templateValue: string) => {
    const template = templates.find((item) => item.value === templateValue) ?? templates[0];
    setFormData((prev) => ({
      ...prev,
      template_type: template.value,
      ai_model: template.model,
      ai_provider: template.provider,
      system_prompt: template.prompt,
    }));
  };

  const addTag = () => {
    const tag = newTag.trim();
    if (!tag) return;
    if (formData.tags?.includes(tag)) {
      setNewTag('');
      return;
    }
    setField('tags', [...(formData.tags ?? []), tag]);
    setNewTag('');
  };

  const removeTag = (tag: string) => {
    setField('tags', (formData.tags ?? []).filter((item) => item !== tag));
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!formData.title?.trim()) {
      toast.error('请输入对话标题');
      return;
    }

    try {
      const created = await createMutation.mutateAsync({
        ...formData,
        title: formData.title.trim(),
      });
      toast.success('对话已创建');
      onSuccess?.(created);
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to create conversation:', error);
      toast.error('创建对话失败');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>新建对话</DialogTitle>
          <DialogDescription>选择模板并填写对话目标，系统会创建一个新的 AI 会话。</DialogDescription>
        </DialogHeader>

        <form onSubmit={submit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2 md:col-span-2">
              <Label>标题</Label>
              <Input value={formData.title ?? ''} onChange={(event) => setField('title', event.target.value)} placeholder="例如：登录流程测试用例设计" />
            </div>

            <div className="space-y-2">
              <Label>模板</Label>
              <Select value={formData.template_type ?? 'general'} onValueChange={applyTemplate}>
                <SelectTrigger>
                  <SelectValue placeholder="选择模板" />
                </SelectTrigger>
                <SelectContent>
                  {templates.map((template) => (
                    <SelectItem key={template.value} value={template.value}>
                      {template.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>分组</Label>
              <Select value={formData.group ?? ConversationGroup.WORK} onValueChange={(value) => setField('group', value as ConversationGroup)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择分组" />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(ConversationGroup).map((group) => (
                    <SelectItem key={group} value={group}>
                      {groupLabels[group]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>AI 模型</Label>
              <Input value={formData.ai_model ?? ''} onChange={(event) => setField('ai_model', event.target.value)} />
            </div>

            <div className="space-y-2">
              <Label>供应商</Label>
              <Input value={formData.ai_provider ?? ''} onChange={(event) => setField('ai_provider', event.target.value)} />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label>目标</Label>
              <Textarea value={formData.goal ?? ''} onChange={(event) => setField('goal', event.target.value)} placeholder="本次对话希望达成的目标" />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label>系统提示词</Label>
              <Textarea rows={4} value={formData.system_prompt ?? ''} onChange={(event) => setField('system_prompt', event.target.value)} />
            </div>
          </div>

          <div className="space-y-2">
            <Label>标签</Label>
            <div className="flex gap-2">
              <Input value={newTag} onChange={(event) => setNewTag(event.target.value)} onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault();
                  addTag();
                }
              }} />
              <Button type="button" variant="outline" onClick={addTag}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {(formData.tags ?? []).map((tag) => (
                <Badge key={tag} variant="secondary" className="gap-1">
                  {tag}
                  <button type="button" onClick={() => removeTag(tag)}>
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={createMutation.isPending}>
              取消
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              创建
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
