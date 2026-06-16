// @ts-nocheck
/**
 * 浠ｇ爜楂樹寒缁勪欢
 * 鏀寔澶氱缂栫▼璇█鐨勮娉曢珮浜拰浠ｇ爜鎿嶄綔
 */
import React, { useState, useCallback } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { 
  Copy, 
  Check, 
  Download, 
  Play, 
  Eye, 
  EyeOff,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../ui/Dialog';
import { cn } from '../../lib/utils';

interface CodeHighlightProps {
  code: string;
  language?: string;
  filename?: string;
  showLineNumbers?: boolean;
  showCopyButton?: boolean;
  showDownloadButton?: boolean;
  showRunButton?: boolean;
  showFullscreenButton?: boolean;
  theme?: 'dark' | 'light';
  maxHeight?: number;
  className?: string;
  onCopy?: (code: string) => void;
  onDownload?: (code: string, filename?: string) => void;
  onRun?: (code: string, language: string) => void;
}

// 鏀寔鐨勫彲鎵ц璇█
const EXECUTABLE_LANGUAGES = [
  'javascript', 'js', 'typescript', 'ts', 
  'python', 'py', 'html', 'css'
];

// 璇█鍒悕鏄犲皠
const LANGUAGE_ALIASES: Record<string, string> = {
  'js': 'javascript',
  'ts': 'typescript',
  'py': 'python',
  'jsx': 'javascript',
  'tsx': 'typescript',
  'vue': 'javascript',
  'svelte': 'javascript'
};

// 璇█鏄剧ず鍚嶇О
const LANGUAGE_NAMES: Record<string, string> = {
  'javascript': 'JavaScript',
  'typescript': 'TypeScript',
  'python': 'Python',
  'java': 'Java',
  'cpp': 'C++',
  'c': 'C',
  'csharp': 'C#',
  'php': 'PHP',
  'ruby': 'Ruby',
  'go': 'Go',
  'rust': 'Rust',
  'swift': 'Swift',
  'kotlin': 'Kotlin',
  'scala': 'Scala',
  'html': 'HTML',
  'css': 'CSS',
  'scss': 'SCSS',
  'sass': 'Sass',
  'less': 'Less',
  'json': 'JSON',
  'xml': 'XML',
  'yaml': 'YAML',
  'yml': 'YAML',
  'toml': 'TOML',
  'ini': 'INI',
  'sql': 'SQL',
  'bash': 'Bash',
  'shell': 'Shell',
  'powershell': 'PowerShell',
  'dockerfile': 'Dockerfile',
  'markdown': 'Markdown',
  'md': 'Markdown'
};

export function CodeHighlight({
  code,
  language = 'text',
  filename,
  showLineNumbers = true,
  showCopyButton = true,
  showDownloadButton = false,
  showRunButton = false,
  showFullscreenButton = true,
  theme = 'dark',
  maxHeight = 400,
  className,
  onCopy,
  onDownload,
  onRun
}: CodeHighlightProps) {
  const [copied, setCopied] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 鏍囧噯鍖栬瑷€鍚嶇О
  const normalizedLanguage = LANGUAGE_ALIASES[language.toLowerCase()] || language.toLowerCase();
  const displayLanguage = LANGUAGE_NAMES[normalizedLanguage] || language.toUpperCase();
  const isExecutable = EXECUTABLE_LANGUAGES.includes(normalizedLanguage);

  // 澶勭悊浠ｇ爜澶嶅埗
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      onCopy?.(code);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy code:', error);
    }
  }, [code, onCopy]);

  // 澶勭悊浠ｇ爜涓嬭浇
  const handleDownload = useCallback(() => {
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `code.${normalizedLanguage}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    onDownload?.(code, filename);
  }, [code, filename, normalizedLanguage, onDownload]);

  // 澶勭悊浠ｇ爜杩愯
  const handleRun = useCallback(() => {
    onRun?.(code, normalizedLanguage);
  }, [code, normalizedLanguage, onRun]);

  // 璁＄畻浠ｇ爜琛屾暟
  const lineCount = code.split('\n').length;
  const shouldShowCollapse = lineCount > 20;

  // 娓叉煋宸ュ叿鏍?
  const renderToolbar = () => (
    <div className="flex items-center justify-between px-4 py-2 bg-gray-800 text-gray-200 text-sm">
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="text-xs">
          {displayLanguage}
        </Badge>
        {filename && (
          <span className="text-gray-400 dark:text-gray-500">{filename}</span>
        )}
        <span className="text-gray-500 dark:text-gray-400">
          {lineCount} 琛?
        </span>
      </div>
      
      <div className="flex items-center gap-1">
        {shouldShowCollapse && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-gray-400 hover:text-white dark:text-gray-500"
            onClick={() => setIsCollapsed(!isCollapsed)}
          >
            {isCollapsed ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
          </Button>
        )}
        
        {showRunButton && isExecutable && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-gray-400 hover:text-white dark:text-gray-500"
            onClick={handleRun}
          >
            <Play className="w-3 h-3" />
          </Button>
        )}
        
        {showDownloadButton && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-gray-400 hover:text-white dark:text-gray-500"
            onClick={handleDownload}
          >
            <Download className="w-3 h-3" />
          </Button>
        )}
        
        {showCopyButton && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-gray-400 hover:text-white dark:text-gray-500"
            onClick={handleCopy}
          >
            {copied ? (
              <Check className="w-3 h-3 text-green-400" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </Button>
        )}
        
        {showFullscreenButton && (
          <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 text-gray-400 hover:text-white dark:text-gray-500"
              >
                <Maximize2 className="w-3 h-3" />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-6xl max-h-[90vh] p-0">
              <DialogHeader className="px-4 py-2 border-b">
                <DialogTitle className="flex items-center gap-2">
                  <Badge variant="secondary">{displayLanguage}</Badge>
                  {filename && <span>{filename}</span>}
                </DialogTitle>
              </DialogHeader>
              <div className="overflow-auto max-h-[calc(90vh-80px)]">
                <SyntaxHighlighter
                  language={normalizedLanguage}
                  style={theme === 'dark' ? oneDark : oneLight}
                  showLineNumbers={showLineNumbers}
                  wrapLines={true}
                  customStyle={{
                    margin: 0,
                    borderRadius: 0,
                    background: 'transparent'
                  }}
                >
                  {code}
                </SyntaxHighlighter>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  );

  // 娓叉煋浠ｇ爜鍐呭
  const renderCode = () => {
    const displayCode = isCollapsed ? code.split('\n').slice(0, 10).join('\n') + '\n...' : code;
    
    return (
      <SyntaxHighlighter
        language={normalizedLanguage}
        style={theme === 'dark' ? oneDark : oneLight}
        showLineNumbers={showLineNumbers}
        wrapLines={true}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          maxHeight: isCollapsed ? 'none' : maxHeight,
          overflow: 'auto'
        }}
      >
        {displayCode}
      </SyntaxHighlighter>
    );
  };

  return (
    <div className={cn(
      'rounded-lg overflow-hidden border border-gray-300 my-4 dark:border-gray-600',
      className
    )}>
      {renderToolbar()}
      <div className="relative">
        {renderCode()}
        
        {/* 鎶樺彔鐘舵€佹彁绀?*/}
        {isCollapsed && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-gray-900 to-transparent h-8 flex items-end justify-center pb-1">
            <Button
              variant="ghost"
              size="sm"
              className="text-gray-400 hover:text-white text-xs dark:text-gray-500"
              onClick={() => setIsCollapsed(false)}
            >
              鏄剧ず鍏ㄩ儴 ({lineCount - 10} 琛?
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * 鍐呰仈浠ｇ爜楂樹寒缁勪欢
 */
export function InlineCode({ 
  code, 
  language,
  className 
}: { 
  code: string; 
  language?: string;
  className?: string;
}) {
  return (
    <code className={cn(
      'bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono dark:bg-gray-800',
      className
    )}>
      {code}
    </code>
  );
}