/**
 * Markdown娓叉煋缁勪欢
 * 鏀寔浠ｇ爜楂樹寒銆佹暟瀛﹀叕寮忋€佽〃鏍肩瓑
 */
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeHighlight from 'rehype-highlight';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import 'katex/dist/katex.min.css';
import 'highlight.js/styles/github.css';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  enableCopy?: boolean;
  enableMath?: boolean;
  enableTables?: boolean;
}

export function MarkdownRenderer({
  content,
  className,
  enableCopy = true,
  enableMath = true,
  enableTables = true
}: MarkdownRendererProps) {
  const [copiedCode, setCopiedCode] = React.useState<string | null>(null);

  // 澶勭悊浠ｇ爜澶嶅埗
  const handleCopyCode = React.useCallback(async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch (error) {
      console.error('Failed to copy code:', error);
    }
  }, []);

  // 鑷畾涔変唬鐮佸潡娓叉煋
  const CodeBlock = React.useCallback(({ 
    node, 
    inline, 
    className: codeClassName, 
    children, 
    ...props 
  }: any) => {
    const match = /language-(\w+)/.exec(codeClassName || '');
    const language = match ? match[1] : '';
    const code = String(children).replace(/\n$/, '');

    if (!inline && language) {
      return (
        <div className="relative group">
          {enableCopy && (
            <Button
              variant="ghost"
              size="sm"
              className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10"
              onClick={() => handleCopyCode(code)}
            >
              {copiedCode === code ? (
                <Check className="w-4 h-4 text-green-600" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </Button>
          )}
          <SyntaxHighlighter
            style={oneDark}
            language={language}
            PreTag="div"
            className="rounded-lg !mt-0 !mb-4"
            {...props}
          >
            {code}
          </SyntaxHighlighter>
        </div>
      );
    }

    return (
      <code 
        className={cn(
          'bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono dark:bg-gray-800',
          codeClassName
        )} 
        {...props}
      >
        {children}
      </code>
    );
  }, [enableCopy, copiedCode, handleCopyCode]);

  // 鑷畾涔夎〃鏍兼覆鏌?
  const Table = React.useCallback(({ children, ...props }: any) => (
    <div className="overflow-x-auto my-4">
      <table className="min-w-full border-collapse border border-gray-300 dark:border-gray-600" {...props}>
        {children}
      </table>
    </div>
  ), []);

  const TableHead = React.useCallback(({ children, ...props }: any) => (
    <thead className="bg-gray-50 dark:bg-gray-800/50" {...props}>
      {children}
    </thead>
  ), []);

  const TableRow = React.useCallback(({ children, ...props }: any) => (
    <tr className="border-b border-gray-200 dark:border-gray-700" {...props}>
      {children}
    </tr>
  ), []);

  const TableCell = React.useCallback(({ children, ...props }: any) => (
    <td className="border border-gray-300 px-4 py-2 dark:border-gray-600" {...props}>
      {children}
    </td>
  ), []);

  const TableHeaderCell = React.useCallback(({ children, ...props }: any) => (
    <th className="border border-gray-300 px-4 py-2 font-semibold text-left dark:border-gray-600" {...props}>
      {children}
    </th>
  ), []);

  // 鑷畾涔夐摼鎺ユ覆鏌?
  const Link = React.useCallback(({ href, children, ...props }: any) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 hover:text-blue-800 underline dark:text-blue-400"
      {...props}
    >
      {children}
    </a>
  ), []);

  // 鑷畾涔夊紩鐢ㄥ潡娓叉煋
  const Blockquote = React.useCallback(({ children, ...props }: any) => (
    <blockquote 
      className="border-l-4 border-gray-300 pl-4 py-2 my-4 bg-gray-50 italic dark:bg-gray-800/50 dark:border-gray-600"
      {...props}
    >
      {children}
    </blockquote>
  ), []);

  // 鑷畾涔夊垪琛ㄦ覆鏌?
  const List = React.useCallback(({ ordered, children, ...props }: any) => {
    const Component = ordered ? 'ol' : 'ul';
    return (
      <Component 
        className={cn(
          'my-4 space-y-1',
          ordered ? 'list-decimal list-inside' : 'list-disc list-inside'
        )}
        {...props}
      >
        {children}
      </Component>
    );
  }, []);

  const ListItem = React.useCallback(({ children, ...props }: any) => (
    <li className="leading-relaxed" {...props}>
      {children}
    </li>
  ), []);

  // 鑷畾涔夋爣棰樻覆鏌?
  const Heading = React.useCallback(({ level, children, ...props }: any) => {
    const Component = `h${level}` as keyof JSX.IntrinsicElements;
    const sizeClasses = {
      1: 'text-2xl font-bold mt-6 mb-4',
      2: 'text-xl font-bold mt-5 mb-3',
      3: 'text-lg font-semibold mt-4 mb-2',
      4: 'text-base font-semibold mt-3 mb-2',
      5: 'text-sm font-semibold mt-2 mb-1',
      6: 'text-xs font-semibold mt-2 mb-1'
    };

    return (
      <Component 
        className={cn(sizeClasses[level as keyof typeof sizeClasses], 'text-gray-900 dark:text-gray-100')}
        {...props}
      >
        {children}
      </Component>
    );
  }, []);

  // 閰嶇疆remark鍜宺ehype鎻掍欢
  const remarkPlugins = [
    remarkGfm, // GitHub Flavored Markdown
    ...(enableMath ? [remarkMath] : [])
  ];

  const rehypePlugins = [
    ...(enableMath ? [rehypeKatex] : []),
    rehypeHighlight
  ];

  return (
    <div className={cn('prose prose-sm max-w-none', className)}>
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={{
          code: CodeBlock,
          ...(enableTables ? {
            table: Table,
            thead: TableHead,
            tr: TableRow,
            td: TableCell,
            th: TableHeaderCell,
          } : {}),
          a: Link,
          blockquote: Blockquote,
          ul: List,
          ol: List,
          li: ListItem,
          h1: (props) => <Heading level={1} {...props} />,
          h2: (props) => <Heading level={2} {...props} />,
          h3: (props) => <Heading level={3} {...props} />,
          h4: (props) => <Heading level={4} {...props} />,
          h5: (props) => <Heading level={5} {...props} />,
          h6: (props) => <Heading level={6} {...props} />,
          p: ({ children, ...props }) => (
            <p className="mb-4 leading-relaxed text-gray-800 dark:text-gray-200" {...props}>
              {children}
            </p>
          ),
          strong: ({ children, ...props }) => (
            <strong className="font-semibold text-gray-900 dark:text-gray-100" {...props}>
              {children}
            </strong>
          ),
          em: ({ children, ...props }) => (
            <em className="italic text-gray-700 dark:text-gray-300" {...props}>
              {children}
            </em>
          ),
          hr: (props) => (
            <hr className="my-6 border-gray-300 dark:border-gray-600" {...props} />
          )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}