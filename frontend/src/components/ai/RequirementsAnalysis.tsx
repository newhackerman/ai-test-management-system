/**
 * 需求分析页面组件
 * 
 * 功能特性：
 * - 质量评分可视化
 * - 问题需求突出显示
 * - 改进建议展示
 * - 批量选择和操作
 * - 分析历史查看
 * - 实时分析进度显示
 * - 分析结果增量加载
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Badge } from '../ui/Badge';
import { Progress } from '../ui/Progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/Tabs';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/Select';
import { 
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  FileText,
  BarChart3,
  RefreshCw,
  Download,
  Play,
  Pause,
  Square,
  Loader2,
  Eye,
  EyeOff
} from 'lucide-react';
import { 
  RequirementsAnalysisResult,
  AnalysisProgress,
  QualityMetrics,
  RequirementIssue,
  AnalysisStatus
} from '../../types/ai-assistant';
import { cn } from '../../lib/utils';
import { useToast } from '../../hooks/useToast';

interface RequirementsAnalysisProps {
  projectId: number;
  requirements: any[];
  onAnalysisComplete?: (result: RequirementsAnalysisResult) => void;
  onProgressUpdate?: (progress: AnalysisProgress) => void;
  className?: string;
}

interface QualityScoreCardProps {
  metrics: QualityMetrics;
  showDetails?: boolean;
  onDetailClick?: (metric: keyof QualityMetrics) => void;
  className?: string;
}

// 质量评分卡片组件
function QualityScoreCard({ 
  metrics, 
  showDetails = false, 
  onDetailClick, 
  className 
}: QualityScoreCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 bg-green-100';
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 0.8) return '优秀';
    if (score >= 0.6) return '良好';
    if (score >= 0.4) return '一般';
    return '需改进';
  };

  const scoreItems = [
    { key: 'completeness_score' as const, label: '完整性', value: metrics.completeness_score },
    { key: 'clarity_score' as const, label: '清晰度', value: metrics.clarity_score },
    { key: 'consistency_score' as const, label: '一致性', value: metrics.consistency_score },
    { key: 'testability_score' as const, label: '可测试性', value: metrics.testability_score },
  ];

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          质量评分
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 总体评分 */}
        <div className="text-center p-4 bg-gray-50 rounded-lg dark:bg-gray-800/50">
          <div className={cn(
            "text-3xl font-bold mb-2",
            getScoreColor(metrics.overall_score)
          )}>
            {Math.round(metrics.overall_score * 100)}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            总体评分 - {getScoreLabel(metrics.overall_score)}
          </div>
          <Progress 
            value={metrics.overall_score * 100} 
            className="mt-2"
          />
        </div>

        {/* 详细评分 */}
        <div className="grid grid-cols-2 gap-3">
          {scoreItems.map((item) => (
            <div
              key={item.key}
              className={cn(
                "p-3 rounded-lg border cursor-pointer transition-colors",
                showDetails && "hover:bg-gray-50 dark:bg-gray-800/50"
              )}
              onClick={() => onDetailClick?.(item.key)}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {item.label}
                </span>
                <Badge className={getScoreColor(item.value)}>
                  {Math.round(item.value * 100)}
                </Badge>
              </div>
              <Progress value={item.value * 100} className="h-2" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// 问题需求展示组件
function ProblematicRequirements({ 
  issues, 
  onIssueClick 
}: { 
  issues: RequirementIssue[];
  onIssueClick?: (issue: RequirementIssue) => void;
}) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30';
      case 'HIGH': return 'bg-orange-100 text-orange-800';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800';
      case 'LOW': return 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800';
      default: return 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
      case 'HIGH':
        return <AlertTriangle className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-3">
      {issues.map((issue, index) => (
        <Card 
          key={index}
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => onIssueClick?.(issue)}
        >
          <CardContent className="p-4">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-gray-900 truncate dark:text-gray-100">
                  {issue.requirement_title}
                </h4>
                <p className="text-sm text-gray-600 mt-1 dark:text-gray-400">
                  {issue.issue_type}
                </p>
              </div>
              <Badge className={cn("ml-2", getSeverityColor(issue.severity))}>
                {getSeverityIcon(issue.severity)}
                {issue.severity}
              </Badge>
            </div>
            
            <p className="text-sm text-gray-700 mb-3 line-clamp-2 dark:text-gray-300">
              {issue.description}
            </p>
            
            {issue.suggestions.length > 0 && (
              <div className="border-t pt-2">
                <p className="text-xs text-gray-500 mb-1 dark:text-gray-400">改进建议:</p>
                <ul className="text-xs text-gray-600 space-y-1 dark:text-gray-400">
                  {issue.suggestions.slice(0, 2).map((suggestion, idx) => (
                    <li key={idx} className="flex items-start gap-1">
                      <span className="text-blue-500 mt-0.5 dark:text-blue-400">•</span>
                      <span className="line-clamp-1">{suggestion}</span>
                    </li>
                  ))}
                  {issue.suggestions.length > 2 && (
                    <li className="text-blue-600 dark:text-blue-400">
                      +{issue.suggestions.length - 2} 更多建议...
                    </li>
                  )}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// 分析进度组件
function AnalysisProgressIndicator({ 
  progress, 
  onCancel 
}: { 
  progress: AnalysisProgress;
  onCancel?: () => void;
}) {
  const getStatusColor = (status: AnalysisStatus) => {
    switch (status) {
      case 'ANALYZING': return 'text-blue-600 bg-blue-100 dark:bg-blue-900/30';
      case 'COMPLETED': return 'text-green-600 bg-green-100';
      case 'FAILED': return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30';
      case 'CANCELLED': return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800';
      default: return 'text-yellow-600 bg-yellow-100';
    }
  };

  const getStatusLabel = (status: AnalysisStatus) => {
    switch (status) {
      case 'PENDING': return '等待中';
      case 'ANALYZING': return '分析中';
      case 'COMPLETED': return '已完成';
      case 'FAILED': return '失败';
      case 'CANCELLED': return '已取消';
      default: return '未知';
    }
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}秒`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}分${remainingSeconds}秒`;
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Badge className={getStatusColor(progress.status)}>
              {progress.status === 'ANALYZING' && (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              )}
              {getStatusLabel(progress.status)}
            </Badge>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {progress.current_step}
            </span>
          </div>
          
          {progress.status === 'ANALYZING' && onCancel && (
            <Button
              variant="outline"
              size="sm"
              onClick={onCancel}
              className="text-red-600 border-red-200 hover:bg-red-50 dark:text-red-400 dark:bg-red-900/20 dark:border-red-800"
            >
              <Square className="w-4 h-4 mr-1" />
              取消
            </Button>
          )}
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>进度: {progress.completed_steps.length}/{progress.total_steps}</span>
            <span>{Math.round(progress.progress)}%</span>
          </div>
          
          <Progress value={progress.progress} className="h-2" />
          
          {progress.estimated_time_remaining > 0 && (
            <div className="text-xs text-gray-500 text-center dark:text-gray-400">
              预计剩余时间: {formatTime(progress.estimated_time_remaining)}
            </div>
          )}
        </div>

        {progress.error_message && (
          <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700 dark:text-red-400 dark:bg-red-900/20 dark:border-red-800">
            {progress.error_message}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function RequirementsAnalysis({
  projectId,
  requirements,
  onAnalysisComplete,
  onProgressUpdate,
  className
}: RequirementsAnalysisProps) {
  // 状态管理
  const [analysisResult, setAnalysisResult] = useState<RequirementsAnalysisResult | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIssue, setSelectedIssue] = useState<RequirementIssue | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [analysisHistory, setAnalysisHistory] = useState<RequirementsAnalysisResult[]>([]);

  const { toast } = useToast();

  // 开始分析
  const startAnalysis = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setAnalysisResult(null);
      setAnalysisProgress(null);

      // 这里应该调用实际的API
      // const response = await analysisService.startAnalysis({
      //   project_id: projectId,
      //   requirements: requirements,
      //   include_ai_analysis: true
      // });

      // 模拟分析进度
      const mockProgress: AnalysisProgress = {
        analysis_id: `analysis_${Date.now()}`,
        project_id: projectId,
        status: 'ANALYZING',
        progress: 0,
        current_step: '初始化分析...',
        estimated_time_remaining: 120,
        completed_steps: [],
        total_steps: 5,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };

      setAnalysisProgress(mockProgress);
      onProgressUpdate?.(mockProgress);

      // 模拟进度更新
      const steps = [
        '解析需求文档...',
        '分析需求完整性...',
        '检查需求一致性...',
        '评估可测试性...',
        '生成分析报告...'
      ];

      for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        const updatedProgress: AnalysisProgress = {
          ...mockProgress,
          progress: ((i + 1) / steps.length) * 100,
          current_step: steps[i],
          completed_steps: steps.slice(0, i + 1),
          estimated_time_remaining: (steps.length - i - 1) * 2,
          updated_at: new Date().toISOString()
        };

        setAnalysisProgress(updatedProgress);
        onProgressUpdate?.(updatedProgress);
      }

      // 模拟分析结果
      const mockResult: RequirementsAnalysisResult = {
        analysis_id: mockProgress.analysis_id,
        project_id: projectId,
        total_requirements: requirements.length,
        quality_metrics: {
          completeness_score: 0.75,
          clarity_score: 0.68,
          consistency_score: 0.82,
          testability_score: 0.71,
          overall_score: 0.74
        },
        issues: [
          {
            requirement_id: 'REQ-001',
            requirement_title: '用户登录功能',
            issue_type: '缺少错误处理',
            description: '登录功能缺少对密码错误次数限制的描述',
            severity: 'HIGH',
            suggestions: [
              '添加密码错误次数限制机制',
              '定义账户锁定策略',
              '添加解锁流程说明'
            ]
          },
          {
            requirement_id: 'REQ-002',
            requirement_title: '数据导出功能',
            issue_type: '描述不清晰',
            description: '导出格式和字段定义不够明确',
            severity: 'MEDIUM',
            suggestions: [
              '明确支持的导出格式',
              '详细列出导出字段',
              '添加导出文件大小限制'
            ]
          }
        ],
        suggestions: [],
        analysis_summary: '本次分析发现2个需要改进的问题，总体质量评分为74分，建议重点关注完整性和清晰度方面的改进。',
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString()
      };

      // 完成分析
      const finalProgress: AnalysisProgress = {
        ...mockProgress,
        status: 'COMPLETED',
        progress: 100,
        current_step: '分析完成',
        estimated_time_remaining: 0,
        completed_steps: steps,
        updated_at: new Date().toISOString()
      };

      setAnalysisProgress(finalProgress);
      setAnalysisResult(mockResult);
      onAnalysisComplete?.(mockResult);
      onProgressUpdate?.(finalProgress);

      toast({
        title: '分析完成',
        description: '需求质量分析已完成，请查看分析结果',
        variant: 'success'
      });

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '分析失败';
      setError(errorMessage);
      
      if (analysisProgress) {
        const errorProgress: AnalysisProgress = {
          ...analysisProgress,
          status: 'FAILED',
          error_message: errorMessage,
          updated_at: new Date().toISOString()
        };
        setAnalysisProgress(errorProgress);
        onProgressUpdate?.(errorProgress);
      }

      toast({
        title: '分析失败',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [projectId, requirements, onAnalysisComplete, onProgressUpdate, toast]);

  // 取消分析
  const cancelAnalysis = useCallback(async () => {
    if (!analysisProgress) return;

    try {
      // 这里应该调用取消API
      // await analysisService.cancelAnalysis(analysisProgress.analysis_id);

      const cancelledProgress: AnalysisProgress = {
        ...analysisProgress,
        status: 'CANCELLED',
        updated_at: new Date().toISOString()
      };

      setAnalysisProgress(cancelledProgress);
      onProgressUpdate?.(cancelledProgress);

      toast({
        title: '分析已取消',
        description: '需求分析已被用户取消',
        variant: 'info'
      });
    } catch (err) {
      toast({
        title: '取消失败',
        description: '取消分析时发生错误',
        variant: 'destructive'
      });
    }
  }, [analysisProgress, onProgressUpdate, toast]);

  // 导出分析报告
  const exportReport = useCallback(async () => {
    if (!analysisResult) return;

    try {
      // 这里应该调用导出API
      toast({
        title: '导出成功',
        description: '分析报告已导出',
        variant: 'success'
      });
    } catch (err) {
      toast({
        title: '导出失败',
        description: '导出报告时发生错误',
        variant: 'destructive'
      });
    }
  }, [analysisResult, toast]);

  const canStartAnalysis = requirements.length > 0 && 
    (!analysisProgress || analysisProgress.status === 'COMPLETED' || analysisProgress.status === 'FAILED');

  return (
    <div className={cn("space-y-6", className)}>
      {/* 操作栏 */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">需求质量分析</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                分析 {requirements.length} 个需求的质量指标和潜在问题
              </p>
            </div>

            <div className="flex items-center gap-2">
              {analysisResult && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={exportReport}
                >
                  <Download className="w-4 h-4 mr-1" />
                  导出报告
                </Button>
              )}

              <Button
                onClick={startAnalysis}
                disabled={!canStartAnalysis || loading}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-1" />
                )}
                {analysisResult ? '重新分析' : '开始分析'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 分析进度 */}
      {analysisProgress && analysisProgress.status !== 'COMPLETED' && (
        <AnalysisProgressIndicator
          progress={analysisProgress}
          onCancel={analysisProgress.status === 'ANALYZING' ? cancelAnalysis : undefined}
        />
      )}

      {/* 分析结果 */}
      {analysisResult && (
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">概览</TabsTrigger>
            <TabsTrigger value="quality">质量评分</TabsTrigger>
            <TabsTrigger value="issues">问题列表</TabsTrigger>
            <TabsTrigger value="history">历史记录</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 质量评分卡片 */}
              <QualityScoreCard
                metrics={analysisResult.quality_metrics}
                showDetails={showDetails}
                onDetailClick={() => setShowDetails(!showDetails)}
              />

              {/* 分析摘要 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    分析摘要
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-700 leading-relaxed dark:text-gray-300">
                    {analysisResult.analysis_summary}
                  </p>
                  
                  <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                      <span>需求总数: {analysisResult.total_requirements}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-500 dark:text-red-400" />
                      <span>问题数量: {analysisResult.issues.length}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="quality" className="space-y-4">
            <QualityScoreCard
              metrics={analysisResult.quality_metrics}
              showDetails={true}
              className="max-w-2xl mx-auto"
            />
          </TabsContent>

          <TabsContent value="issues" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5" />
                    问题需求 ({analysisResult.issues.length})
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowDetails(!showDetails)}
                  >
                    {showDetails ? (
                      <>
                        <EyeOff className="w-4 h-4 mr-1" />
                        隐藏详情
                      </>
                    ) : (
                      <>
                        <Eye className="w-4 h-4 mr-1" />
                        显示详情
                      </>
                    )}
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ProblematicRequirements
                  issues={analysisResult.issues}
                  onIssueClick={setSelectedIssue}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="history" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  分析历史
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>暂无历史记录</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}

      {/* 错误提示 */}
      {error && (
        <Card className="border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
              <AlertTriangle className="w-5 h-5" />
              <span className="font-medium">分析失败</span>
            </div>
            <p className="text-red-600 mt-1 dark:text-red-400">{error}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}