import React, { useMemo, useRef, useState } from 'react';
import {
  FileText,
  Paperclip,
  Send,
  Square,
  Trash2,
  Type,
  Wand2,
  X
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Textarea } from '../ui/Textarea';
import { ContentType } from '../../services/conversation-service';
import { cn } from '../../lib/utils';

interface Template {
  id: string;
  name: string;
  content: string;
  description?: string;
}

interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  action: string;
  description: string;
}

interface MessageInputProps {
  onSend: (content: string, contentType?: ContentType, metadata?: Record<string, any>) => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  minHeight?: number;
  maxHeight?: number;
  supportedTypes?: ContentType[];
  defaultContentType?: ContentType;
  autoDetectContentType?: boolean;
  showTemplates?: boolean;
  showFileUpload?: boolean;
  showVoiceInput?: boolean;
  showEmojiPicker?: boolean;
  showHistory?: boolean;
  showSuggestions?: boolean;
  showWordCount?: boolean;
  showTypingIndicator?: boolean;
  isStreaming?: boolean;
  onStopStreaming?: () => void;
  streamingProgress?: number;
  onChange?: (content: string) => void;
  onFocus?: () => void;
  onBlur?: () => void;
  onTyping?: (isTyping: boolean) => void;
  onFileUpload?: (files: File[]) => void;
  onTemplateSelect?: (template: Template) => void;
  onVoiceInput?: (transcript: string) => void;
  enableAutoSave?: boolean;
  enableOfflineMode?: boolean;
  enableSmartSuggestions?: boolean;
  enableMultiLanguage?: boolean;
  templates?: Template[];
  suggestions?: string[];
  shortcuts?: KeyboardShortcut[];
  fileTypes?: string[];
  maxFileSize?: number;
  className?: string;
}

const defaultTemplates: Template[] = [
  {
    id: 'test-case',
    name: '测试用例设计',
    content: '请根据以下需求设计测试用例，包含正常流程、异常流程、边界值和预期结果：\n\n'
  },
  {
    id: 'defect-analysis',
    name: '缺陷分析',
    content: '请分析以下缺陷现象，给出可能原因、复现路径、影响范围和修复建议：\n\n'
  },
  {
    id: 'code-review',
    name: '代码审查',
    content: '请审查以下代码，重点关注可读性、可靠性、安全性和性能问题：\n\n'
  }
];

const detectContentType = (content: string, fallback: ContentType) => {
  const trimmed = content.trim();
  if (/^```[\s\S]*```$/.test(trimmed)) return ContentType.CODE;
  if (/^#{1,6}\s|\*\*.+\*\*|^\s*[-*]\s/m.test(trimmed)) return ContentType.MARKDOWN;
  return fallback;
};

export function MessageInput({
  onSend,
  disabled = false,
  placeholder = '输入消息，按 Ctrl + Enter 发送',
  maxLength = 8000,
  minHeight = 96,
  maxHeight = 240,
  supportedTypes = [ContentType.TEXT, ContentType.MARKDOWN, ContentType.CODE],
  defaultContentType = ContentType.TEXT,
  autoDetectContentType = true,
  showTemplates = true,
  showFileUpload = true,
  showSuggestions = true,
  showWordCount = true,
  isStreaming = false,
  onStopStreaming,
  onChange,
  onFocus,
  onBlur,
  onTyping,
  onFileUpload,
  onTemplateSelect,
  templates = defaultTemplates,
  suggestions = [],
  fileTypes,
  maxFileSize = 10 * 1024 * 1024,
  className
}: MessageInputProps) {
  const [content, setContent] = useState('');
  const [contentType, setContentType] = useState<ContentType>(defaultContentType);
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const effectiveContentType = useMemo(
    () => (autoDetectContentType ? detectContentType(content, contentType) : contentType),
    [autoDetectContentType, content, contentType]
  );

  const canSend = content.trim().length > 0 && !disabled && !isStreaming;
  const visibleSuggestions = suggestions.filter((item) => item.toLowerCase().includes(content.toLowerCase())).slice(0, 3);

  const handleContentChange = (value: string) => {
    if (value.length > maxLength) return;
    setContent(value);
    onChange?.(value);
    onTyping?.(value.length > 0);
  };

  const handleSend = () => {
    const text = content.trim();
    if (!text || disabled || isStreaming) return;

    onSend(text, effectiveContentType, {
      attachments: files.map((file) => ({
        name: file.name,
        size: file.size,
        type: file.type
      }))
    });
    setContent('');
    setFiles([]);
    onChange?.('');
    onTyping?.(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    const validFiles = selectedFiles.filter((file) => file.size <= maxFileSize);
    setFiles((prev) => [...prev, ...validFiles]);
    onFileUpload?.(validFiles);
    event.target.value = '';
  };

  const applyTemplate = (template: Template) => {
    setContent((prev) => `${prev}${prev ? '\n\n' : ''}${template.content}`);
    onTemplateSelect?.(template);
  };

  return (
    <div className={cn('border-t bg-white p-4', className)}>
      {showTemplates && templates.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {templates.slice(0, 4).map((template) => (
            <Button key={template.id} type="button" variant="outline" size="sm" onClick={() => applyTemplate(template)}>
              <Wand2 className="mr-1 h-3.5 w-3.5" />
              {template.name}
            </Button>
          ))}
        </div>
      )}

      {showSuggestions && visibleSuggestions.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {visibleSuggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              className="rounded-md border px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:bg-gray-800/50 dark:hover:bg-gray-800"
              onClick={() => handleContentChange(suggestion)}
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

      {files.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {files.map((file, index) => (
            <Badge key={`${file.name}-${index}`} variant="secondary" className="gap-1">
              <FileText className="h-3 w-3" />
              {file.name}
              <button
                type="button"
                className="ml-1"
                onClick={() => setFiles((prev) => prev.filter((_, fileIndex) => fileIndex !== index))}
                aria-label="移除附件"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      <div className="rounded-lg border bg-white focus-within:ring-2 focus-within:ring-blue-200 dark:bg-gray-800">
        <Textarea
          value={content}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(event) => handleContentChange(event.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={onFocus}
          onBlur={onBlur}
          style={{ minHeight, maxHeight }}
          className="resize-none border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
        />

        <div className="flex flex-wrap items-center justify-between gap-2 border-t px-3 py-2">
          <div className="flex items-center gap-2">
            {showFileUpload && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept={fileTypes?.join(',')}
                  className="hidden"
                  onChange={handleFileChange}
                />
                <Button type="button" variant="ghost" size="sm" onClick={() => fileInputRef.current?.click()} disabled={disabled}>
                  <Paperclip className="h-4 w-4" />
                </Button>
              </>
            )}
            <select
              value={contentType}
              onChange={(event) => setContentType(event.target.value as ContentType)}
              disabled={disabled}
              className="h-8 rounded-md border bg-white px-2 text-xs dark:bg-gray-800"
            >
              {supportedTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
            <Badge variant="outline" className="gap-1">
              <Type className="h-3 w-3" />
              {effectiveContentType}
            </Badge>
          </div>

          <div className="flex items-center gap-2">
            {showWordCount && (
              <span className={cn('text-xs text-gray-500 dark:text-gray-400', content.length > maxLength * 0.9 && 'text-orange-600')}>
                {content.length}/{maxLength}
              </span>
            )}
            {content && (
              <Button type="button" variant="ghost" size="sm" onClick={() => handleContentChange('')}>
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
            {isStreaming ? (
              <Button type="button" variant="destructive" size="sm" onClick={onStopStreaming}>
                <Square className="mr-1 h-4 w-4" />
                停止
              </Button>
            ) : (
              <Button type="button" size="sm" disabled={!canSend} onClick={handleSend}>
                <Send className="mr-1 h-4 w-4" />
                发送
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default MessageInput;
