/**
 * 需求AI分析组件
 * 
 * 提供需求智能分析功能的React组件，包括：
 * 1. 实时质量分析
 * 2. 优化建议展示
 * 3. 冲突检测结果
 * 4. 分析结果可视化
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { 
  Brain, 
  CheckCircle, 
  AlertTriangle, 
  Lightbulb, 
  Target,
  Clock,
  TrendingUp,
  AlertCircle
} from 'lucide-react';

// 类型定义
interface QualityAnalysis {
  overall_score: number;
  completeness_score: number;
  consistency_score: number;
  clarity_score: number;
  testability_score: number;
  feasibility_score: number;
  traceability_score: number;
  complexity_estimate: string;
  effort_estimate: number;
  improvement_suggestions: string[];
  risk_factors: string[];
  confidence_level: number;
  analysis_time: number;
}

interface ConflictAnalysis {
  has_conflicts: boolean;
  conflict_types: string[];
  conflicting_requirements: Array<{
    requirement_id: string;
    title: string;
    conflict_description: string;
  }>;
  resolution_suggestions: string[];
  severity_level: string;
}

interface OptimizationResult {
  requirement_id?: string;
  overall_quality_score: number;
  improvement_potential: number;
  improvements_count: number;
  conflicts_count: number;
  dependencies_count: number;
  best_practices_count: number;
  analysis_time: number;
  confidence_score: number;
}

interface RealTimeAnalysis {
  analysis_type: string;
  score: number;
  suggestions: string[];
  issues: string[];
  processing_time: number;
}

interface RequirementAIAnalysisProps {
  title: string;
  description: string;
  acceptanceCriteria?: string;
  requirementType?: string;
  existingRequirements?: Array<any>;
  projectContext?: Record<string, any>;
  onAnalysisComplete?: (analysis: any) => void;
}

const RequirementAIAnalysis: React.FC<RequirementAIAnalysisProps> = ({
  title,
  description,
  acceptanceCriteria,
  requirementType,
  existingRequirements = [],
  projectContext,
  onAnalysisComplete
}) => {
  // 状态管理
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [qualityAnalysis, setQualityAnalysis] = useState<QualityAnalysis | null>(null);
  const [conflictAnalysis, setConflictAnalysis] = useState<ConflictAnalysis | null>(null);
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null);
  const [realTimeAnalysis, setRealTimeAnalysis] = useState<RealTimeAnalysis | null>(null);
  const [activeTab, setActiveTab] = useState('quality');
  const [error, setError] = useState<string | null>(null);

  // API调用函数
  const analyzeQuality = useCallback(async () => {
    try {
      setIsAnalyzing(true);
      setError(null);

      const response = await fetch('/api/v1/ai-assistant/requirement-analysis/quality-analysis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          title,
          description,
          acceptance_criteria: acceptanceCriteria,
          requirement_type: requirementType,
          project_context: projectContext
        })
      });

      if (!response.ok) {
        throw new Error('质量分析失败');
      }

      const result = await response.json();
      setQualityAnalysis(result);
      
      if (onAnalysisComplete) {
        onAnalysisComplete({ type: 'quality', result });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '分析失败');
    } finally {
      setIsAnalyzing(false);
    }
  }, [title, description, acceptanceCriteria, requirementType, projectContext, onAnalysisComplete]);

  const detectConflicts = useCallback(async () => {
    if (existingRequirements.length === 0) return;

    try {
      setIsAnalyzing(true);
      setError(null);

      const response = await fetch('/api/v1/ai-assistant/requirement-analysis/conflict-detection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          current_requirement: {
            title,
            description,
            type: requirementType
          },
          existing_requirements: existingRequirements
        })
      });

      if (!response.ok) {
        throw new Error('冲突检测失败');
      }

      const result = await response.json();
      setConflictAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '冲突检测失败');
    } finally {
      setIsAnalyzing(false);
    }
  }, [title, description, requirementType, existingRequirements]);

  const generateOptimization = useCallback(async () => {
    try {
      setIsAnalyzing(true);
      setError(null);

      const response = await fetch('/api/v1/ai-assistant/requirement-analysis/optimization', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          title,
          description,
          acceptance_criteria: acceptanceCriteria,
          requirement_type: requirementType,
          existing_requirements: existingRequirements,
          project_context: projectContext
        })
      });

      if (!response.ok) {
        throw new Error('优化分析失败');
      }

      const result = await response.json();
      setOptimizationResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '优化分析失败');
    } finally {
      setIsAnalyzing(false);
    }
  }, [title, description, acceptanceCriteria, requirementType, existingRequirements, projectContext]);

  const performRealTimeAnalysis = useCallback(async (analysisType: string) => {
    try {
      const response = await fetch('/api/v1/ai-assistant/requirement-analysis/real-time-analysis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          content: `${title}\n\n${description}`,
          analysis_type: analysisType
        })
      });

      if (!response.ok) {
        throw new Error('实时分析失败');
      }

      const result = await response.json();
      setRealTimeAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '实时分析失败');
    }
  }, [title, description]);

  // 获取质量评分颜色
  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600';
    if (score >= 6) return 'text-yellow-600';
    return 'text-red-600';
  };

  // 获取复杂度标签颜色
  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'simple': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'complex': return 'bg-orange-100 text-orange-800';
      case 'very_complex': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  // 获取严重程度颜色
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'critical': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* 错误提示 */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* 操作按钮 */}
      <div className="flex gap-2 flex-wrap">
        <Button 
          onClick={analyzeQuality} 
          disabled={isAnalyzing || !title || !description}
          className="flex items-center gap-2"
        >
          <Brain className="h-4 w-4" />
          {isAnalyzing ? '分析中...' : '质量分析'}
        </Button>
        
        <Button 
          onClick={detectConflicts} 
          disabled={isAnalyzing || existingRequirements.length === 0}
          variant="outline"
          className="flex items-center gap-2"
        >
          <AlertTriangle className="h-4 w-4" />
          冲突检测
        </Button>
        
        <Button 
          onClick={generateOptimization} 
          disabled={isAnalyzing || !title || !description}
          variant="outline"
          className="flex items-center gap-2"
        >
          <Lightbulb className="h-4 w-4" />
          优化建议
        </Button>
      </div>

      {/* 实时分析按钮 */}
      <div className="flex gap-2">
        <Button 
          size="sm"
          variant="ghost"
          onClick={() => performRealTimeAnalysis('quality')}
          disabled={!title || !description}
        >
          快速质量检查
        </Button>
        <Button 
          size="sm"
          variant="ghost"
          onClick={() => performRealTimeAnalysis('completeness')}
          disabled={!title || !description}
        >
          完整性检查
        </Button>
        <Button 
          size="sm"
          variant="ghost"
          onClick={() => performRealTimeAnalysis('clarity')}
          disabled={!title || !description}
        >
          清晰度检查
        </Button>
      </div>

      {/* 分析结果展示 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="quality">质量分析</TabsTrigger>
          <TabsTrigger value="conflicts">冲突检测</TabsTrigger>
          <TabsTrigger value="optimization">优化建议</TabsTrigger>
          <TabsTrigger value="realtime">实时分析</TabsTrigger>
        </TabsList>

        {/* 质量分析结果 */}
        <TabsContent value="quality">
          {qualityAnalysis ? (
            <div className="space-y-4">
              {/* 总体评分 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="h-5 w-5" />
                    总体质量评分
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4">
                    <div className={`text-3xl font-bold ${getScoreColor(qualityAnalysis.overall_score)}`}>
                      {qualityAnalysis.overall_score.toFixed(1)}
                    </div>
                    <div className="flex-1">
                      <Progress value={qualityAnalysis.overall_score * 10} className="h-2" />
                    </div>
                    <Badge className={getComplexityColor(qualityAnalysis.complexity_estimate)}>
                      {qualityAnalysis.complexity_estimate}
                    </Badge>
                  </div>
                  <div className="mt-2 text-sm text-gray-600">
                    预估工作量: {qualityAnalysis.effort_estimate} 人天 | 
                    置信度: {(qualityAnalysis.confidence_level * 100).toFixed(0)}% |
                    分析耗时: {qualityAnalysis.analysis_time.toFixed(1)}s
                  </div>
                </CardContent>
              </Card>

              {/* 各维度评分 */}
              <Card>
                <CardHeader>
                  <CardTitle>详细评分</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    {[
                      { label: '完整性', score: qualityAnalysis.completeness_score },
                      { label: '一致性', score: qualityAnalysis.consistency_score },
                      { label: '清晰性', score: qualityAnalysis.clarity_score },
                      { label: '可测试性', score: qualityAnalysis.testability_score },
                      { label: '可行性', score: qualityAnalysis.feasibility_score },
                      { label: '可追溯性', score: qualityAnalysis.traceability_score }
                    ].map(({ label, score }) => (
                      <div key={label} className="flex items-center justify-between">
                        <span className="text-sm">{label}</span>
                        <div className="flex items-center gap-2">
                          <Progress value={score * 10} className="w-20 h-2" />
                          <span className={`text-sm font-medium ${getScoreColor(score)}`}>
                            {score.toFixed(1)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* 改进建议 */}
              {qualityAnalysis.improvement_suggestions.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-5 w-5" />
                      改进建议
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {qualityAnalysis.improvement_suggestions.map((suggestion, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                          <span className="text-sm">{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* 风险因素 */}
              {qualityAnalysis.risk_factors.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5" />
                      风险因素
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {qualityAnalysis.risk_factors.map((risk, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                          <span className="text-sm">{risk}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <Brain className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">点击"质量分析"按钮开始分析需求质量</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* 冲突检测结果 */}
        <TabsContent value="conflicts">
          {conflictAnalysis ? (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5" />
                    冲突检测结果
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {conflictAnalysis.has_conflicts ? (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2">
                        <Badge variant="destructive">发现冲突</Badge>
                        <Badge className={getSeverityColor(conflictAnalysis.severity_level)}>
                          {conflictAnalysis.severity_level}
                        </Badge>
                      </div>
                      
                      <div>
                        <h4 className="font-medium mb-2">冲突类型:</h4>
                        <div className="flex gap-2 flex-wrap">
                          {conflictAnalysis.conflict_types.map((type, index) => (
                            <Badge key={index} variant="outline">{type}</Badge>
                          ))}
                        </div>
                      </div>

                      <div>
                        <h4 className="font-medium mb-2">冲突需求:</h4>
                        <ul className="space-y-2">
                          {conflictAnalysis.conflicting_requirements.map((req, index) => (
                            <li key={index} className="p-3 bg-red-50 rounded-lg">
                              <div className="font-medium">{req.title}</div>
                              <div className="text-sm text-gray-600">{req.conflict_description}</div>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div>
                        <h4 className="font-medium mb-2">解决建议:</h4>
                        <ul className="space-y-2">
                          {conflictAnalysis.resolution_suggestions.map((suggestion, index) => (
                            <li key={index} className="flex items-start gap-2">
                              <Lightbulb className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                              <span className="text-sm">{suggestion}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-2" />
                      <p className="text-green-600 font-medium">未发现冲突</p>
                      <p className="text-sm text-gray-500">当前需求与已有需求不存在冲突</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <AlertTriangle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">点击"冲突检测"按钮检测需求冲突</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* 优化建议结果 */}
        <TabsContent value="optimization">
          {optimizationResult ? (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    优化分析结果
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">
                        {optimizationResult.improvements_count}
                      </div>
                      <div className="text-sm text-gray-600">改进建议</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-600">
                        {optimizationResult.conflicts_count}
                      </div>
                      <div className="text-sm text-gray-600">冲突数量</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">
                        {optimizationResult.dependencies_count}
                      </div>
                      <div className="text-sm text-gray-600">依赖关系</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">
                        {optimizationResult.best_practices_count}
                      </div>
                      <div className="text-sm text-gray-600">最佳实践</div>
                    </div>
                  </div>
                  
                  <div className="mt-4 pt-4 border-t">
                    <div className="flex justify-between text-sm text-gray-600">
                      <span>改进潜力: {(optimizationResult.improvement_potential * 100).toFixed(0)}%</span>
                      <span>置信度: {(optimizationResult.confidence_score * 100).toFixed(0)}%</span>
                      <span>分析耗时: {optimizationResult.analysis_time.toFixed(1)}s</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <TrendingUp className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">点击"优化建议"按钮生成优化方案</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* 实时分析结果 */}
        <TabsContent value="realtime">
          {realTimeAnalysis ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  实时分析结果 - {realTimeAnalysis.analysis_type}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center gap-4">
                    <div className={`text-2xl font-bold ${getScoreColor(realTimeAnalysis.score)}`}>
                      {realTimeAnalysis.score.toFixed(1)}
                    </div>
                    <Progress value={realTimeAnalysis.score * 10} className="flex-1 h-2" />
                    <span className="text-sm text-gray-500">
                      {realTimeAnalysis.processing_time.toFixed(2)}s
                    </span>
                  </div>

                  {realTimeAnalysis.suggestions.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2">建议:</h4>
                      <ul className="space-y-1">
                        {realTimeAnalysis.suggestions.map((suggestion, index) => (
                          <li key={index} className="flex items-start gap-2">
                            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                            <span className="text-sm">{suggestion}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {realTimeAnalysis.issues.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2">问题:</h4>
                      <ul className="space-y-1">
                        {realTimeAnalysis.issues.map((issue, index) => (
                          <li key={index} className="flex items-start gap-2">
                            <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                            <span className="text-sm">{issue}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">点击上方的快速检查按钮进行实时分析</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default RequirementAIAnalysis;