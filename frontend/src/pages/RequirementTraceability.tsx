import React, { useMemo, useState } from 'react';
import {
  AlertTriangle,
  BarChart3,
  CheckCircle,
  Download,
  Filter,
  GitBranch,
  Network,
  RefreshCw,
  Search,
  Target,
  XCircle
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';

interface TraceabilityFilters {
  search: string;
  requirement_type: string;
  trace_type: string;
  coverage_status: string;
}

interface TraceabilityRow {
  id: string;
  requirement: string;
  type: string;
  design: string;
  testCase: string;
  defect: string;
  coverage: 'COVERED' | 'PARTIAL' | 'UNCOVERED';
}

const rows: TraceabilityRow[] = [
  { id: 'REQ-001', requirement: '用户登录', type: '功能需求', design: 'AUTH-DES-01', testCase: 'TC-AUTH-001', defect: '-', coverage: 'COVERED' },
  { id: 'REQ-002', requirement: '密码重置', type: '功能需求', design: 'AUTH-DES-02', testCase: 'TC-AUTH-009', defect: 'BUG-102', coverage: 'COVERED' },
  { id: 'REQ-003', requirement: '权限校验', type: '约束需求', design: 'RBAC-DES-01', testCase: '-', defect: '-', coverage: 'PARTIAL' },
  { id: 'REQ-004', requirement: '审计日志', type: '非功能需求', design: '-', testCase: '-', defect: '-', coverage: 'UNCOVERED' }
];

const coverageLabels = {
  COVERED: '已覆盖',
  PARTIAL: '部分覆盖',
  UNCOVERED: '未覆盖'
};

const coverageClassNames = {
  COVERED: 'bg-green-100 text-green-700',
  PARTIAL: 'bg-yellow-100 text-yellow-700',
  UNCOVERED: 'bg-red-100 text-red-700'
};

export default function RequirementTraceability() {
  const [filters, setFilters] = useState<TraceabilityFilters>({
    search: '',
    requirement_type: '',
    trace_type: '',
    coverage_status: ''
  });
  const [activeTab, setActiveTab] = useState('matrix');
  const [refreshing, setRefreshing] = useState(false);

  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      const keyword = filters.search.trim().toLowerCase();
      const matchesKeyword = !keyword || [row.id, row.requirement, row.design, row.testCase, row.defect].join(' ').toLowerCase().includes(keyword);
      const matchesType = !filters.requirement_type || row.type === filters.requirement_type;
      const matchesCoverage = !filters.coverage_status || row.coverage === filters.coverage_status;
      return matchesKeyword && matchesType && matchesCoverage;
    });
  }, [filters]);

  const statistics = useMemo(() => {
    const total = filteredRows.length;
    const covered = filteredRows.filter((row) => row.coverage === 'COVERED').length;
    const partial = filteredRows.filter((row) => row.coverage === 'PARTIAL').length;
    const uncovered = filteredRows.filter((row) => row.coverage === 'UNCOVERED').length;
    return {
      total_requirements: total,
      traced_requirements: covered + partial,
      untraced_requirements: uncovered,
      coverage_percentage: total ? Math.round(((covered + partial * 0.5) / total) * 100) : 0,
      gap_count: uncovered,
      partial_count: partial
    };
  }, [filteredRows]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await new Promise((resolve) => window.setTimeout(resolve, 500));
    setRefreshing(false);
  };

  const handleExport = () => {
    const csv = ['需求编号,需求名称,类型,设计,测试用例,缺陷,覆盖状态']
      .concat(filteredRows.map((row) => [row.id, row.requirement, row.type, row.design, row.testCase, row.defect, coverageLabels[row.coverage]].join(',')))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'requirement-traceability.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  const CoverageIcon = statistics.coverage_percentage >= 90 ? CheckCircle : statistics.coverage_percentage >= 70 ? AlertTriangle : XCircle;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">需求追溯管理</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            刷新数据
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            导出 CSV
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard label="总需求数" value={statistics.total_requirements} icon={<Target className="h-8 w-8 text-blue-400" />} />
        <StatCard
          label="追溯覆盖率"
          value={`${statistics.coverage_percentage}%`}
          icon={<CoverageIcon className="h-8 w-8 text-green-500" />}
        />
        <StatCard label="已追溯需求" value={statistics.traced_requirements} icon={<GitBranch className="h-8 w-8 text-green-400" />} />
        <StatCard label="追溯缺口" value={statistics.gap_count} icon={<AlertTriangle className="h-8 w-8 text-red-400" />} />
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 lg:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="搜索需求、设计、测试用例或缺陷..."
                className="pl-10"
                value={filters.search}
                onChange={(event) => setFilters((prev) => ({ ...prev, search: event.target.value }))}
              />
            </div>
            <select
              className="h-10 rounded-md border px-3 text-sm"
              value={filters.requirement_type}
              onChange={(event) => setFilters((prev) => ({ ...prev, requirement_type: event.target.value }))}
            >
              <option value="">全部类型</option>
              <option value="功能需求">功能需求</option>
              <option value="非功能需求">非功能需求</option>
              <option value="约束需求">约束需求</option>
            </select>
            <select
              className="h-10 rounded-md border px-3 text-sm"
              value={filters.coverage_status}
              onChange={(event) => setFilters((prev) => ({ ...prev, coverage_status: event.target.value }))}
            >
              <option value="">全部覆盖状态</option>
              <option value="COVERED">已覆盖</option>
              <option value="PARTIAL">部分覆盖</option>
              <option value="UNCOVERED">未覆盖</option>
            </select>
            <Button variant="outline" size="sm">
              <Filter className="mr-2 h-4 w-4" />
              更多筛选
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="matrix">追溯矩阵</TabsTrigger>
          <TabsTrigger value="graph">关系图</TabsTrigger>
          <TabsTrigger value="coverage">覆盖分析</TabsTrigger>
          <TabsTrigger value="gaps">缺口分析</TabsTrigger>
        </TabsList>

        <TabsContent value="matrix">
          <Card>
            <CardHeader>
              <CardTitle>追溯矩阵</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] border-collapse text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50 text-left">
                      <th className="p-3">需求编号</th>
                      <th className="p-3">需求名称</th>
                      <th className="p-3">类型</th>
                      <th className="p-3">设计</th>
                      <th className="p-3">测试用例</th>
                      <th className="p-3">缺陷</th>
                      <th className="p-3">覆盖状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRows.map((row) => (
                      <tr key={row.id} className="border-b">
                        <td className="p-3 font-medium">{row.id}</td>
                        <td className="p-3">{row.requirement}</td>
                        <td className="p-3">{row.type}</td>
                        <td className="p-3">{row.design}</td>
                        <td className="p-3">{row.testCase}</td>
                        <td className="p-3">{row.defect}</td>
                        <td className="p-3">
                          <Badge className={`border-0 ${coverageClassNames[row.coverage]}`}>{coverageLabels[row.coverage]}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="graph">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-5 w-5" />
                关系图
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                {filteredRows.map((row) => (
                  <div key={row.id} className="rounded-lg border p-4">
                    <div className="font-medium">{row.id} · {row.requirement}</div>
                    <div className="mt-3 flex flex-wrap gap-2 text-sm">
                      <Badge variant="outline">设计 {row.design}</Badge>
                      <Badge variant="outline">用例 {row.testCase}</Badge>
                      {row.defect !== '-' && <Badge variant="destructive">{row.defect}</Badge>}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="coverage">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                覆盖分析
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Alert>
                <AlertDescription>
                  当前筛选范围覆盖率为 {statistics.coverage_percentage}%，其中 {statistics.partial_count} 个需求只有部分追溯链路。
                </AlertDescription>
              </Alert>
              <div className="h-3 overflow-hidden rounded-full bg-gray-100">
                <div className="h-full bg-green-500" style={{ width: `${statistics.coverage_percentage}%` }} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="gaps">
          <Card>
            <CardHeader>
              <CardTitle>缺口分析</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {filteredRows.filter((row) => row.coverage !== 'COVERED').map((row) => (
                <Alert key={row.id} className="border-yellow-200 bg-yellow-50">
                  <AlertDescription>
                    {row.id}「{row.requirement}」追溯不完整，请补充设计文档或测试用例关联。
                  </AlertDescription>
                </Alert>
              ))}
              {statistics.gap_count === 0 && <div className="text-sm text-muted-foreground">当前筛选范围暂无未覆盖缺口。</div>}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: React.ReactNode; icon: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">{label}</p>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
          </div>
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}
