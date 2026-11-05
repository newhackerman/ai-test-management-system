import React from 'react'
import { Link } from 'react-router-dom'
import { BarChart3, FileSpreadsheet, FileText } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'

/**
 * 报告管理总览页。
 *
 * The routes table lazy-loads this page for `/reports`; the file was
 * missing from the repo, which made Vite fail to transform the routes
 * module and left the whole frontend blank (no page could mount).
 * This page aggregates the existing report areas instead of duplicating
 * them: 测试报告、Allure 报告、数据统计。
 */
const reportEntries = [
  {
    title: '测试报告',
    description: '查看已生成的测试报告，按项目、计划与执行结果筛选。',
    path: '/test-manager/reports',
    icon: FileSpreadsheet,
  },
  {
    title: 'Allure 报告',
    description: '管理 Allure 测试报告，查看执行明细与历史记录。',
    path: '/allure-reports',
    icon: FileText,
  },
  {
    title: '数据统计',
    description: '项目、需求、用例与缺陷的统计概览与趋势分析。',
    path: '/statistics',
    icon: BarChart3,
  },
]

const Reports: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">报告管理</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          集中查看测试报告、Allure 报告与数据统计。
        </p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {reportEntries.map((entry) => {
          const Icon = entry.icon
          return (
            <Link key={entry.path} to={entry.path}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Icon className="h-5 w-5" />
                    {entry.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{entry.description}</CardDescription>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

export default Reports
