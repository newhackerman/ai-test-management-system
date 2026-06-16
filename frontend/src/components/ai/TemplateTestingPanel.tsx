import React, { useMemo, useState } from 'react';
import { BarChart3, CheckCircle, Play, Plus, RefreshCw, Trash2, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Textarea } from '@/components/ui/Textarea';
import { useToast } from '@/hooks/useToast';
import {
  BatchTemplateTestResponse,
  PromptTemplate,
  TemplateEvaluationResponse,
  TemplateTestResponse,
  TestScenario,
  promptTemplateService
} from '@/services/prompt-template-service';

interface TemplateTestingPanelProps {
  template: PromptTemplate;
  onClose?: () => void;
}

interface TestConfiguration {
  ai_provider: string;
  ai_model: string;
  contextText: string;
}

const parseJson = (value: string): Record<string, unknown> => {
  if (!value.trim()) return {};
  const parsed = JSON.parse(value);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('上下文必须是 JSON 对象');
  }
  return parsed as Record<string, unknown>;
};

const formatDate = (value?: string) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

export function TemplateTestingPanel({ template, onClose }: TemplateTestingPanelProps) {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('single');
  const [isLoading, setIsLoading] = useState(false);
  const [testConfig, setTestConfig] = useState<TestConfiguration>({
    ai_provider: template.supported_providers?.[0] || 'openai',
    ai_model: template.supported_models?.[0] || 'gpt-4',
    contextText: JSON.stringify(template.example_context || template.default_values || {}, null, 2)
  });
  const [newScenario, setNewScenario] = useState({
    name: '',
    contextText: '{}',
    expected_output: ''
  });
  const [testScenarios, setTestScenarios] = useState<TestScenario[]>([]);
  const [testResults, setTestResults] = useState<TemplateTestResponse | null>(null);
  const [batchResults, setBatchResults] = useState<BatchTemplateTestResponse | null>(null);
  const [evaluationResults, setEvaluationResults] = useState<TemplateEvaluationResponse | null>(null);

  const providers = useMemo(
    () => (template.supported_providers?.length ? template.supported_providers : ['openai', 'anthropic']),
    [template.supported_providers]
  );
  const models = useMemo(
    () => (template.supported_models?.length ? template.supported_models : ['gpt-4', 'gpt-3.5-turbo']),
    [template.supported_models]
  );

  const runSafely = async (action: () => Promise<void>) => {
    try {
      setIsLoading(true);
      await action();
    } catch (error) {
      toast({
        title: '测试失败',
        description: error instanceof Error ? error.message : '执行测试时发生未知错误',
        variant: 'destructive'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSingleTest = () =>
    runSafely(async () => {
      const result = await promptTemplateService.testTemplate(template.id, {
        context: parseJson(testConfig.contextText),
        ai_provider: testConfig.ai_provider,
        ai_model: testConfig.ai_model
      });
      setTestResults(result);
      toast({
        title: '测试完成',
        description: `成功率 ${(result.success_rate * 100).toFixed(1)}%`,
        variant: result.success ? 'success' : 'destructive'
      });
    });

  const handleAddScenario = () => {
    try {
      const scenario: TestScenario = {
        name: newScenario.name.trim() || `场景 ${testScenarios.length + 1}`,
        context: parseJson(newScenario.contextText),
        expected_output: newScenario.expected_output || undefined,
        ai_provider: testConfig.ai_provider,
        ai_model: testConfig.ai_model
      };
      setTestScenarios((prev) => [...prev, scenario]);
      setNewScenario({ name: '', contextText: '{}', expected_output: '' });
    } catch (error) {
      toast({
        title: '场景格式错误',
        description: error instanceof Error ? error.message : '请检查 JSON 格式',
        variant: 'destructive'
      });
    }
  };

  const handleScenarioTest = () =>
    runSafely(async () => {
      const scenarios = testScenarios.length
        ? testScenarios
        : [{ name: '默认场景', context: parseJson(testConfig.contextText) }];
      const result = await promptTemplateService.testTemplate(template.id, {
        context: parseJson(testConfig.contextText),
        ai_provider: testConfig.ai_provider,
        ai_model: testConfig.ai_model,
        test_scenarios: scenarios
      });
      setTestResults(result);
      toast({
        title: '场景测试完成',
        description: `${result.successful_tests}/${result.total_tests} 个场景通过`,
        variant: result.success_rate >= 0.8 ? 'success' : 'destructive'
      });
    });

  const handleBatchTest = () =>
    runSafely(async () => {
      const cases = testScenarios.length
        ? testScenarios.map((scenario) => ({
            name: scenario.name,
            context: scenario.context,
            expected_output: scenario.expected_output
          }))
        : [{ name: '默认用例', context: parseJson(testConfig.contextText) }];
      const result = await promptTemplateService.batchTestTemplate(template.id, {
        test_cases: cases,
        ai_providers: providers.slice(0, 2),
        ai_models: models.slice(0, 2)
      });
      setBatchResults(result);
      toast({
        title: '批量测试完成',
        description: `整体成功率 ${(result.overall_success_rate * 100).toFixed(1)}%`,
        variant: 'success'
      });
    });

  const handlePerformanceEvaluation = () =>
    runSafely(async () => {
      const testData = (testScenarios.length ? testScenarios : [{ context: parseJson(testConfig.contextText) }]).map(
        (scenario) => ({
          context: scenario.context,
          ai_provider: testConfig.ai_provider,
          ai_model: testConfig.ai_model
        })
      );
      const result = await promptTemplateService.evaluateTemplatePerformance(template.id, {
        criteria: ['response_time', 'token_usage', 'success_rate'],
        test_data: testData
      });
      setEvaluationResults(result);
      toast({
        title: '性能评估完成',
        description: `平均响应 ${result.performance_metrics.avg_response_time.toFixed(2)}s`,
        variant: 'success'
      });
    });

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">模板测试</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">{template.title || template.name}</p>
        </div>
        {onClose && (
          <Button variant="outline" onClick={onClose}>
            返回
          </Button>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">测试配置</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span>AI 提供商</span>
            <select
              value={testConfig.ai_provider}
              className="h-10 w-full rounded-md border px-3"
              onChange={(event) => setTestConfig((prev) => ({ ...prev, ai_provider: event.target.value }))}
            >
              {providers.map((provider) => (
                <option key={provider} value={provider}>
                  {provider}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span>模型</span>
            <select
              value={testConfig.ai_model}
              className="h-10 w-full rounded-md border px-3"
              onChange={(event) => setTestConfig((prev) => ({ ...prev, ai_model: event.target.value }))}
            >
              {models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm md:col-span-2">
            <span>测试上下文 JSON</span>
            <Textarea
              value={testConfig.contextText}
              rows={6}
              onChange={(event) => setTestConfig((prev) => ({ ...prev, contextText: event.target.value }))}
            />
          </label>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="single">单次测试</TabsTrigger>
          <TabsTrigger value="scenarios">场景测试</TabsTrigger>
          <TabsTrigger value="batch">批量与性能</TabsTrigger>
        </TabsList>

        <TabsContent value="single" className="space-y-4">
          <Button onClick={handleSingleTest} disabled={isLoading}>
            {isLoading ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            执行单次测试
          </Button>
          {testResults && <ResultCard result={testResults} />}
        </TabsContent>

        <TabsContent value="scenarios" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">新增测试场景</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                placeholder="场景名称"
                value={newScenario.name}
                onChange={(event) => setNewScenario((prev) => ({ ...prev, name: event.target.value }))}
              />
              <Textarea
                rows={5}
                placeholder="场景上下文 JSON"
                value={newScenario.contextText}
                onChange={(event) => setNewScenario((prev) => ({ ...prev, contextText: event.target.value }))}
              />
              <Textarea
                rows={3}
                placeholder="期望输出，可选"
                value={newScenario.expected_output}
                onChange={(event) => setNewScenario((prev) => ({ ...prev, expected_output: event.target.value }))}
              />
              <Button variant="outline" onClick={handleAddScenario}>
                <Plus className="mr-2 h-4 w-4" />
                添加场景
              </Button>
            </CardContent>
          </Card>

          <div className="space-y-2">
            {testScenarios.map((scenario, index) => (
              <div key={`${scenario.name}-${index}`} className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <div className="font-medium">{scenario.name}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">{Object.keys(scenario.context).length} 个变量</div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setTestScenarios((prev) => prev.filter((_, itemIndex) => itemIndex !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          <Button onClick={handleScenarioTest} disabled={isLoading}>
            <Play className="mr-2 h-4 w-4" />
            执行场景测试
          </Button>
          {testResults && <ResultCard result={testResults} />}
        </TabsContent>

        <TabsContent value="batch" className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button onClick={handleBatchTest} disabled={isLoading}>
              <BarChart3 className="mr-2 h-4 w-4" />
              批量测试
            </Button>
            <Button variant="outline" onClick={handlePerformanceEvaluation} disabled={isLoading}>
              <RefreshCw className="mr-2 h-4 w-4" />
              性能评估
            </Button>
          </div>

          {batchResults && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">批量测试结果</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Badge variant="secondary">整体成功率 {(batchResults.overall_success_rate * 100).toFixed(1)}%</Badge>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {batchResults.total_provider_model_combinations} 个模型组合，{batchResults.total_test_cases} 个测试用例
                </div>
              </CardContent>
            </Card>
          )}

          {evaluationResults && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">性能评估结果</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-3">
                <Metric label="平均响应" value={`${evaluationResults.performance_metrics.avg_response_time.toFixed(2)}s`} />
                <Metric label="平均 Token" value={evaluationResults.performance_metrics.avg_token_usage.toFixed(0)} />
                <Metric label="总 Token" value={evaluationResults.performance_metrics.total_token_usage} />
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ResultCard({ result }: { result: TemplateTestResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          {result.success ? <CheckCircle className="h-4 w-4 text-green-600" /> : <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />}
          测试结果
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant={result.success ? 'default' : 'destructive'}>成功率 {(result.success_rate * 100).toFixed(1)}%</Badge>
          <Badge variant="outline">
            {result.successful_tests}/{result.total_tests} 通过
          </Badge>
          <Badge variant="secondary">{formatDate(result.test_timestamp)}</Badge>
        </div>
        <pre className="max-h-64 overflow-auto rounded-md bg-gray-50 p-3 text-xs whitespace-pre-wrap dark:bg-gray-800/50">
          {result.rendered_content}
        </pre>
        <div className="space-y-2">
          {result.test_results.map((item, index) => (
            <div key={`${item.scenario_name}-${index}`} className="rounded-md border p-3 text-sm">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-medium">{item.scenario_name || `结果 ${index + 1}`}</span>
                <Badge variant={item.success ? 'default' : 'destructive'}>{item.success ? '通过' : '失败'}</Badge>
              </div>
              <div className="text-gray-500 dark:text-gray-400">
                {item.ai_provider} / {item.ai_model} · {item.response_time.toFixed(2)}s · {item.token_usage} tokens
              </div>
              {item.response && <p className="mt-2 whitespace-pre-wrap">{item.response}</p>}
              {item.error && <p className="mt-2 text-red-600 dark:text-red-400">{item.error}</p>}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border p-3">
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}

export default TemplateTestingPanel;
